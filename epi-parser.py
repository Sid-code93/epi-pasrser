import re
import matplotlib.pyplot as plt
from tabulate import tabulate

def parse_lay_file(filepath):
    layers = {}
    current_layer = None
    with open(filepath, 'r') as file:
        for line in file:
            line = line.strip()
            if line.startswith("definelayer("):
                current_layer = line.split("(")[1].split(")")[0]
                layers[current_layer] = {"shutters": [], "rate": None}
            elif line.startswith("rate(") and current_layer:
                rate = float(re.search(r'rate\(([\d.]+)\)', line).group(1))
                layers[current_layer]["rate"] = rate
            elif line.startswith("open(") and current_layer:
                shutters = re.findall(r'\w+', line)
                layers[current_layer]["shutters"] = shutters[1:]
            elif line.startswith("enddefine"):
                current_layer = None
    return layers

def parse_epi_file_with_loops(filepath, lay_data):
    layer_stack = []
    with open(filepath, 'r') as file:
        lines = file.readlines()

    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith("for("):
            m = re.match(r'for\((\w+),\s*(\d+),\s*([\d.]+)\)', line)
            if m:
                var, iterations, step = m.groups()
                iterations = int(iterations)
                i += 1
                block = []
                while i < len(lines) and not lines[i].strip().startswith("next("):
                    block.append(lines[i].strip())
                    i += 1
                block_layers = []
                for bl in block:
                    parsed = parse_layer_line(bl, lay_data)
                    if parsed:
                        block_layers.append(parsed)
                layer_stack.append({
                    "Group": True,
                    "Repeat": iterations,
                    "Layers": block_layers
                })
        elif line.startswith("layer("):
            parsed = parse_layer_line(line, lay_data)
            if parsed:
                layer_stack.append(parsed)
        i += 1

    if not any(l.get("Material", "").lower() == "substrate" for l in layer_stack if isinstance(l, dict)):
        layer_stack.insert(0,{
            "Material": "Substrate",
            "Composition": "",
            "Thickness (nm)": 500,
            "Time (s)": 0,
            "Shutters": "",
            "Repeat": 1
        })

    return layer_stack

def parse_layer_line(line, lay_data):
    match = re.match(r'layer\((\w+),([\d.]+)([a-z]+)\)(.*)', line)
    if not match:
        return None
    
    material, value, unit, comment = match.groups()
    #material, value, unit, label = m.groups()
    composition_match = re.search(r'(Al\d+GaAs|In\d+GaAs|AlAs|GaAs)', comment)
    composition = composition_match.group(1) if composition_match else "Unknown"

    value = float(value)

    # Handle shutterzu (idle time)
    if material == "shutterzu":
        return {
            "Material": "Idle",
            "Thickness (nm)": 0,
            "Time (s)": value if unit == "s" else 0,
            "Shutters": [],
            "Composition": "None",
            "Growth Rate (nm/h)": 0
        }
        #continue
    rate = lay_data[material]["rate"]
    shutters = ", ".join(lay_data[material]["shutters"])
    if unit == "nm":
        thickness = value
        time_s = thickness * 3600 / rate
    elif unit == "s":
        time_s = value
        thickness = rate * time_s / 3600
    
    else:
        return None
    return {
        "Material": material,
        "Composition": composition,
        "Thickness (nm)": round(thickness, 2),
        "Time (s)": round(time_s, 2),
        "Shutters": shutters,
        "Repeat": 1
    }

def flatten_layers(layers):
    flat = []
    for item in layers:
        if isinstance(item, dict) and item.get("Group"):
            for l in item["Layers"]:
                l_copy = l.copy()
                l_copy["Repeat"] = item["Repeat"]
                l_copy["Thickness (nm)"] *= item["Repeat"]
                l_copy["Time (s)"] *= item["Repeat"]
                flat.append(l_copy)
        else:
            flat.append(item)
    return flat

def plot_layer_structure(layers):
    flat_layers = flatten_layers(layers)
    fig, ax = plt.subplots(figsize=(6, len(flat_layers)*0.5))
    y = 0
    for layer in reversed(flat_layers):
        label = f"{layer['Material']}"
        if layer.get("Composition"):
            label += f" ({layer['Composition']})"
        if layer.get("Repeat", 1) > 1:
            label += f" ×{layer['Repeat']}"
        label += f", {layer['Thickness (nm)']} nm"
        ax.barh(y, width=1, height=0.8, color='skyblue', edgecolor='black')
        ax.text(0.5, y, label, ha='center', va='center')
        y += 1
    ax.axis('off')
    plt.tight_layout()
    plt.show()

def print_layer_table(layers):
    flat_layers = flatten_layers(layers)
    headers = ["#", "Material", "Composition", "Thickness (nm)", "Time (s)", "Shutters", "Repeat"]
    table = [[i+1, l["Material"], l.get("Composition", ""), l["Thickness (nm)"], l["Time (s)"], l["Shutters"], l.get("Repeat", 1)] for i, l in enumerate(flat_layers)]
    print(tabulate(table, headers=headers, tablefmt="fancy_grid"))

# Example usage
# lay_data = parse_lay_file("example.lay")
# layer_stack = parse_epi_file_with_loops("example.epi", lay_data)


# ======== Example Run ========
lay_file = r"C:\Users\sid34gu\Documents\Data\EPI files\Programs\C5661.lay"
epi_file = r"C:\Users\sid34gu\Documents\Data\EPI files\Programs\C5661.epi"


lay_data = parse_lay_file(lay_file)
layer_stack = parse_epi_file_with_loops(epi_file, lay_data)
print_layer_table(layer_stack)
plot_layer_structure(layer_stack)