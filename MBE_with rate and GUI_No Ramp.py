import tkinter as tk
from tkinter import filedialog, messagebox
import os
import re
from tabulate import tabulate
import matplotlib.pyplot as plt

# ======================= File Parsers (Unchanged) =======================

# ... (Insert `parse_lay_file`, `parse_epi_file`, `get_material_family`, `plot_layer_structure` here)
# ... (Insert `print_layer_table` but modify it to return a string instead of printing)

def parse_lay_file(filepath):
    layers = {}
    current_layer = None
    with open(filepath, 'r') as file:
        for line in file:
            line = line.strip()
            if line.startswith("definelayer("):
                current_layer = line.split("(")[1].split(")")[0]
                layers[current_layer] = {"shutters": [], "rate": None, "composition": None}
            elif line.startswith("rate(") and current_layer:
                rate = float(re.search(r'rate\(([\d.]+)\)', line).group(1))
                layers[current_layer]["rate"] = rate
            elif line.startswith("open(") and current_layer:
                shutters = re.findall(r'\w+', line)
                layers[current_layer]["shutters"] = shutters[1:]
            elif line.startswith("enddefine"):
                current_layer = None
    return layers

def parse_epi_file(filepath, lay_data):
    layer_stack = []
    with open(filepath, 'r') as file:
        for line in file:
            line = line.strip()
            if line.startswith("layer("):
                match = re.match(r'layer\((\w+),([\d.]+)([a-z]+)\)(.*)', line)
                if not match:
                    continue
                material, value, unit, comment = match.groups()
                composition_match = re.search(r'(Al\d+GaAs|In\d+GaAs)', comment)
                composition = composition_match.group(1) if composition_match else "Unknown"
                value = float(value)
                if material == "shutterzu":
                    layer_stack.append({
                        "Material": "Idle", "Thickness (nm)": 0, "Time (s)": value if unit == "s" else 0,
                        "Shutters": [], "Composition": "None", "Growth Rate (nm/h)": 0
                    })
                    continue
                if material not in lay_data:
                    continue
                shutters = lay_data[material]["shutters"]
                rate_nm_per_h = lay_data[material]["rate"]
                if unit == "s":
                    time_s = value
                    thickness_nm = rate_nm_per_h * time_s / 3600
                elif unit == "nm":
                    thickness_nm = value
                    time_s = thickness_nm * 3600 / rate_nm_per_h
                else:
                    continue
                layer_stack.append({
                    "Material": material, "Thickness (nm)": round(thickness_nm, 2),
                    "Time (s)": round(time_s, 2), "Shutters": ", ".join(shutters),
                    "Composition": composition, "Growth Rate (nm/h)": rate_nm_per_h
                })
    return layer_stack

def get_material_family(material):
    if material == "Idle": return "Idle"
    if "InGa" in material: return "InGaAs"
    if "Ga" in material and "Al" in material: return "AlGaAs"
    if "Ga" in material: return "GaAs"
    if "Al" in material: return "AlAs"
    if "In" in material: return "InAs"
    if material == "Substrate": return "Substrate"
    return "Other"

def plot_layer_structure(layer_stack, metadata):
    fig, ax = plt.subplots(figsize=(10, 6))

    # Build full stack (excluding idle or unknown layers)
    full_stack = [layer for layer in layer_stack if layer['Material'].lower() not in ['idle', 'unknown']]

    num_layers = len(full_stack)
    y_positions = list(range(num_layers))  # one row per layer
    layer_height = 1  # fixed height for visual clarity
    
    family_colors = {
        "GaAs": "#1f77b4",
        "AlGaAs": "#ff7f0e",
        "InGaAs": "#2ca02c",
        "AlAs": "#d62728",
        "InAs": "#9467bd",
        "Idle": "#7f7f7f",
        "Substrate": "#bbbbbb",
        "Other": "#c7c7c7"
    }
    
    for i, layer in enumerate(reversed(full_stack)):
        material = layer["Material"]
        family = get_material_family(material)
        color = family_colors.get(family, "#c7c7c7")

        y = i  # y-position is the row index
        label = f"{material}, {layer['Thickness (nm)']} nm"
        if layer["Composition"] != "None":
            label += f" ({layer['Composition']})"

        # Draw bar
        ax.barh(y=y, width=1, height=layer_height, color=color, edgecolor='black')

        # Center text within the bar (both x and y)
        ax.text(
            0.5,
            y,
            label,
            ha='center',
            va='center',
            fontsize=9,
            color='black'
        )

    # Add title and metadata
    ax.set_title("MBE Sample Structure", fontsize=12)
    ax.text(0.5, num_layers + 0.5, metadata, ha='center', va='bottom', fontsize=10)

    # Styling
    ax.set_xlim(0, 1)
    ax.set_ylim(-0.5, num_layers - 0.5)
    ax.axis('off')
    plt.tight_layout()
    plt.show()

def generate_layer_table(layers):
    headers = ["#", "Material", "Thickness (nm)", "Time (s)", "Shutters", "Composition", "Growth Rate (nm/h)"]
    table = [[i + 1, l["Material"], l["Thickness (nm)"], l["Time (s)"],
              l["Shutters"], l["Composition"], l["Growth Rate (nm/h)"]]
             for i, l in enumerate(layers)]
    return tabulate(table, headers=headers, tablefmt="fancy_grid")

# ======================= GUI =======================

class MBEApp:
    def __init__(self, root):
        self.root = root
        self.root.title("MBE Structure Visualizer")
        self.epi_path = tk.StringVar()
        self.lay_path = tk.StringVar()

        # Entry fields
        self.create_entry("EPI File:", self.epi_path, self.browse_epi).pack()
        self.create_entry("LAY File:", self.lay_path, self.browse_lay).pack()

        # Store Entry widgets, not frames
        self.sample_holder = self.create_labeled_input("Sample Holder:")
        self.tsub_shift = self.create_labeled_input("Tsub Shift (°C):")
        self.wafer_type = self.create_labeled_input("Wafer Type:")
        self.description = self.create_labeled_input("Description / Project:")

        # Submit button
        tk.Button(self.root, text="Generate Report", command=self.generate_report).pack(pady=10)

    def create_entry(self, label_text, var, browse_command):
        frame = tk.Frame(self.root)
        tk.Label(frame, text=label_text).pack(side=tk.LEFT)
        tk.Entry(frame, textvariable=var, width=40).pack(side=tk.LEFT)
        tk.Button(frame, text="Browse", command=browse_command).pack(side=tk.LEFT)
        return frame

    def create_labeled_input(self, label_text):
        frame = tk.Frame(self.root)
        frame.pack()
        tk.Label(frame, text=label_text).pack(side=tk.LEFT)
        entry = tk.Entry(frame, width=40)
        entry.pack(side=tk.LEFT)
        return entry  # Return the Entry widget directly

    def browse_epi(self):
        path = filedialog.askopenfilename(filetypes=[("EPI files", "*.epi")])
        if path:
            self.epi_path.set(path)

    def browse_lay(self):
        path = filedialog.askopenfilename(filetypes=[("LAY files", "*.lay")])
        if path:
            self.lay_path.set(path)

    def generate_report(self):
        epi_file = self.epi_path.get()
        lay_file = self.lay_path.get()
        if not os.path.exists(epi_file) or not os.path.exists(lay_file):
            messagebox.showerror("Error", "EPI or LAY file not found.")
            return

        metadata = (
            f"Holder: {self.sample_holder.get()} | "
            f"Tsub Shift: {self.tsub_shift.get()}°C | "
            f"Wafer: {self.wafer_type.get()}\n"
            f"Project: {self.description.get()}"
        )

        lay_data = parse_lay_file(lay_file)
        layer_stack = parse_epi_file(epi_file, lay_data)
        table_str = generate_layer_table(layer_stack)

        print("\n" + "="*80)
        print("SAMPLE METADATA:\n" + metadata)
        print("="*80)
        print(table_str)

        plot_layer_structure(layer_stack, metadata)

# === Run the GUI ===
if __name__ == "__main__":
    root = tk.Tk()
    app = MBEApp(root)
    root.mainloop()
