import asyncio
import threading
import tkinter as tk
from tkinter import messagebox, ttk

try:
    from bleak import BleakScanner
except ImportError:
    BleakScanner = None

try:
    from winrt.windows.devices.radios import Radio, RadioAccessStatus, RadioKind, RadioState
except ImportError:
    Radio = None
    RadioAccessStatus = None
    RadioKind = None
    RadioState = None


class BluetoothManager(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("ToothManager")
        self.geometry("560x440")
        self.minsize(480, 360)

        self.devices = []
        self.scanning = False
        self.bluetooth_radio = None

        self._build_ui()
        self.after(100, self.refresh_radio_state)

    def _build_ui(self):
        radio_frame = tk.Frame(self)
        radio_frame.pack(fill="x", padx=10, pady=(10, 0))

        tk.Label(radio_frame, text="Bluetooth:").pack(side="left")

        self.radio_button = tk.Button(
            radio_frame,
            text="Checking...",
            width=12,
            command=self.toggle_bluetooth,
        )
        self.radio_button.pack(side="left", padx=8)

        self.radio_status = tk.Label(radio_frame, text="Checking Bluetooth radio...")
        self.radio_status.pack(side="left")

        top = tk.Frame(self)
        top.pack(fill="x", padx=10, pady=10)

        self.scan_button = tk.Button(
            top,
            text="Scan",
            width=12,
            command=self.start_scan,
        )
        self.scan_button.pack(side="left")

        self.status = tk.Label(top, text="Ready", anchor="w")
        self.status.pack(side="left", padx=10)

        columns = ("name", "address")
        self.device_list = ttk.Treeview(
            self,
            columns=columns,
            show="headings",
            selectmode="browse",
        )
        self.device_list.heading("name", text="Device")
        self.device_list.heading("address", text="Address")
        self.device_list.column("name", width=250)
        self.device_list.column("address", width=220)
        self.device_list.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        bottom = tk.Frame(self)
        bottom.pack(fill="x", padx=10, pady=(0, 10))

        tk.Button(
            bottom,
            text="Pair / Connect",
            command=self.pair_or_connect,
        ).pack(side="left")

        tk.Button(
            bottom,
            text="Disconnect",
            command=self.disconnect,
        ).pack(side="left", padx=6)

    def refresh_radio_state(self):
        if Radio is None:
            self.radio_button.config(state="disabled", text="Unavailable")
            self.radio_status.config(text="Install winrt-Windows.Devices.Radios")
            return

        threading.Thread(target=self._radio_state_worker, daemon=True).start()

    def _radio_state_worker(self):
        try:
            radios = asyncio.run(Radio.get_radios_async())
            bluetooth = next(
                (radio for radio in radios if radio.kind == RadioKind.BLUETOOTH),
                None,
            )
            self.after(0, self._radio_state_finished, bluetooth, None)
        except Exception as exc:
            self.after(0, self._radio_state_finished, None, exc)

    def _radio_state_finished(self, radio, error):
        if error:
            self.bluetooth_radio = None
            self.radio_button.config(state="disabled", text="Unavailable")
            self.radio_status.config(text=str(error))
            return

        self.bluetooth_radio = radio

        if radio is None:
            self.radio_button.config(state="disabled", text="Not found")
            self.radio_status.config(text="No Bluetooth radio detected")
            return

        self._update_radio_ui(radio)

    def _update_radio_ui(self, radio):
        state = radio.state

        if state == RadioState.ON:
            self.radio_button.config(state="normal", text="Turn Off")
            self.radio_status.config(text="On")
        elif state == RadioState.OFF:
            self.radio_button.config(state="normal", text="Turn On")
            self.radio_status.config(text="Off")
        elif state == RadioState.DISABLED:
            self.radio_button.config(state="disabled", text="Disabled")
            self.radio_status.config(text="Disabled by hardware or Windows")
        else:
            self.radio_button.config(state="disabled", text="Unknown")
            self.radio_status.config(text="Unknown radio state")

    def toggle_bluetooth(self):
        if self.bluetooth_radio is None:
            return

        self.radio_button.config(state="disabled", text="Changing...")
        threading.Thread(target=self._toggle_radio_worker, daemon=True).start()

    def _toggle_radio_worker(self):
        try:
            access = asyncio.run(Radio.request_access_async())

            if access != RadioAccessStatus.ALLOWED:
                raise RuntimeError(f"Windows denied Bluetooth radio control: {access}")

            target = (
                RadioState.OFF
                if self.bluetooth_radio.state == RadioState.ON
                else RadioState.ON
            )
            status = asyncio.run(self.bluetooth_radio.set_state_async(target))

            if status != RadioAccessStatus.ALLOWED:
                raise RuntimeError(f"Windows denied the requested radio change: {status}")

            self.after(250, self.refresh_radio_state)
        except Exception as exc:
            self.after(0, self._radio_toggle_failed, exc)

    def _radio_toggle_failed(self, error):
        self._update_radio_ui(self.bluetooth_radio)
        messagebox.showerror("Bluetooth", str(error))

    def start_scan(self):
        if self.scanning:
            return

        if BleakScanner is None:
            messagebox.showerror(
                "Missing dependency",
                "Bleak is not installed. Run: python -m pip install bleak",
            )
            return

        self.scanning = True
        self.scan_button.config(state="disabled")
        self.status.config(text="Scanning...")
        self.device_list.delete(*self.device_list.get_children())

        threading.Thread(target=self._scan_worker, daemon=True).start()

    def _scan_worker(self):
        try:
            devices = asyncio.run(BleakScanner.discover(timeout=5))
            self.after(0, self._scan_finished, devices, None)
        except Exception as exc:
            self.after(0, self._scan_finished, [], exc)

    def _scan_finished(self, devices, error):
        self.scanning = False
        self.scan_button.config(state="normal")

        if error:
            self.status.config(text="Scan failed")
            messagebox.showerror("Bluetooth scan failed", str(error))
            return

        self.devices = devices

        for device in devices:
            name = device.name or "Unknown device"
            self.device_list.insert("", "end", values=(name, device.address))

        self.status.config(text=f"Found {len(devices)} device(s)")

    def _selected_device(self):
        selection = self.device_list.selection()
        if not selection:
            messagebox.showinfo("ToothManager", "Select a Bluetooth device first.")
            return None

        index = self.device_list.index(selection[0])
        return self.devices[index]

    def pair_or_connect(self):
        device = self._selected_device()
        if device is None:
            return

        messagebox.showinfo(
            "Not implemented yet",
            "Device discovery is working first. Pairing and connecting come next.",
        )

    def disconnect(self):
        device = self._selected_device()
        if device is None:
            return

        messagebox.showinfo(
            "Not implemented yet",
            "Disconnect support will be added after device discovery.",
        )


if __name__ == "__main__":
    BluetoothManager().mainloop()
