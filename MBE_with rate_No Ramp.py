import re
from tabulate import tabulate
import matplotlib.pyplot as plt

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
                layers[current_layer]["rate"] = rate  # in nm/h
            elif line.startswith("open(") and current_layer:
                shutters = re.findall(r'\w+', line)
                layers[current_layer]["shutters"] = shutters[1:]  # skip 'open'
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

                # Extract composition info (e.g., Al50GaAs, In30GaAs)
                composition_match = re.search(r'(Al\d+GaAs|In\d+GaAs)', comment)
                composition = composition_match.group(1) if composition_match else "Unknown"

                value = float(value)

                # Handle shutterzu (idle time)
                if material == "shutterzu":
                    layer_stack.append({
                        "Material": "Idle",
                        "Thickness (nm)": 0,
                        "Time (s)": value if unit == "s" else 0,
                        "Shutters": [],
                        "Composition": "None",
                        "Growth Rate (nm/h)": 0
                    })
                    continue

                # Lookup rate and shutters
                if material not in lay_data:
                    print(f"Warning: {material} not in .lay file.")
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
                    "Material": material,
                    "Thickness (nm)": round(thickness_nm, 2),
                    "Time (s)": round(time_s, 2),
                    "Shutters": ", ".join(shutters),
                    "Composition": composition,
                    "Growth Rate (nm/h)": rate_nm_per_h
                })

    return layer_stack

def print_layer_table(layers):
    headers = ["#", "Material", "Thickness (nm)", "Time (s)", "Shutters", "Composition", "Growth Rate (nm/h)"]
    table = [
        [i+1, l["Material"], l["Thickness (nm)"], l["Time (s)"], l["Shutters"], l["Composition"], l["Growth Rate (nm/h)"]]
        for i, l in enumerate(layers)
    ]
    print(tabulate(table, headers=headers, tablefmt="fancy_grid"))

def get_material_family(material):
    if material == "Idle":
        return "Idle"
    elif "InGa" in material:
        return "InGaAs"
    elif "Ga" in material and "Al" in material:
        return "AlGaAs"
    elif "Ga" in material:
        return "GaAs"
    elif "Al" in material:
        return "AlAs"
    elif "In" in material:
        return "InAs"
    elif material == "Substrate":
        return "Substrate"
    else:
        return "Other"

def plot_layer_structure(layers, substrate_thickness_nm=100, scale_factor=0.5):
    # Insert substrate at the beginning
    substrate_layer = {
        "Material": "Substrate",
        "Thickness (nm)": substrate_thickness_nm,
        "Time (s)": 0,
        "Shutters": "GaAs",
        "Composition": "None",
        "Growth Rate (nm/h)": 0
    }
    full_stack = [substrate_layer] + layers

    # Rescale the thickness of all layers for better visibility
    max_thickness = max([layer["Thickness (nm)"] for layer in full_stack])
    scaling_factor = scale_factor / max_thickness

    # Create the plot
    fig, ax = plt.subplots(figsize=(12, 3))
    current_pos = 0

    # Define colors by material family
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

    legend_entries = {}

    for i, layer in enumerate(full_stack):
        thickness = layer["Thickness (nm)"]
        if thickness == 0:
            continue

        # Rescale the thickness
        scaled_thickness = thickness * scaling_factor

        material = layer["Material"]
        family = get_material_family(material)
        color = family_colors.get(family, "#c7c7c7")

        # Create the bar for the layer
        bar = ax.barh(0, scaled_thickness, left=current_pos, height=1, color=color, edgecolor='k')

        # Label with thickness and composition
        composition_label = f"{material} ({layer['Composition']})"
        ax.text(current_pos + scaled_thickness / 2, 0.5,
                f"{thickness:.0f} nm\n{composition_label}",
                ha='center', va='center', fontsize=8, rotation=90 if scaled_thickness < 0.5 else 0)

        if family not in legend_entries:
            legend_entries[family] = bar

        current_pos += scaled_thickness

    # Set axis limits and labels
    ax.set_xlim(0, current_pos)
    ax.set_ylim(-0.5, 1.5)
    ax.set_yticks([])
    ax.set_xlabel("Growth Direction →")
    ax.set_title("MBE Layer Structure (Left = Substrate)")

    # Add legend for material families
    ax.legend(legend_entries.values(), legend_entries.keys(),
              bbox_to_anchor=(1.05, 1), loc='upper left', title="Material Family")

    plt.tight_layout()
    plt.show()

# === Usage ===
lay_file = r"C:\Users\sid34gu\Documents\Data\EPI files\C5682.lay"
epi_file = r"C:\Users\sid34gu\Documents\Data\EPI files\C5682.epi"

lay_data = parse_lay_file(lay_file)
layer_stack = parse_epi_file(epi_file, lay_data)
print_layer_table(layer_stack)
plot_layer_structure(layer_stack)
