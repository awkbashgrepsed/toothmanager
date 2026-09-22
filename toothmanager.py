import asyncio
import threading
import tkinter as tk
from tkinter import messagebox, ttk

try:
    from bleak import BleakScanner
except ImportError:
    BleakScanner = None


class BluetoothManager(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("ToothManager")
        self.geometry("560x400")
        self.minsize(480, 320)

        self.devices = []
        self.scanning = False

        self._build_ui()

    def _build_ui(self):
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
