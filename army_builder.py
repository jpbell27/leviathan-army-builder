import streamlit as st
import pandas as pd
import random
import json
import math

@st.cache_data
def load_data():
    ships = pd.read_csv("ships.csv")
    captains = pd.read_csv("captains.csv")
    fighters = pd.read_csv("fighters.csv")
    return ships, captains, fighters

ships_df, captains_df, fighters_df = load_data()


# App title
st.title("Aetherstream: Leviathan Army Builder")

st.markdown(
    "[📘 How to Use This App](https://github.com/jpbell27/leviathan-army-builder/blob/main/README.md)",
    unsafe_allow_html=True
)

# Sidebar
st.sidebar.header("Build Your Force")
faction = st.sidebar.selectbox("Select Faction", ships_df["Faction"].unique())

#getting ships by faction
@st.cache_data
def filter_by_faction(faction, ships_df, captains_df, fighters_df):
    return (
        ships_df[ships_df["Faction"] == faction],
        captains_df[captains_df["Faction"] == faction],
        fighters_df[fighters_df["Faction"] == faction]
    )

filtered_ships, filtered_captains, filtered_fighters = filter_by_faction(
    faction, ships_df, captains_df, fighters_df
)

# Allow multiple of the same ship
st.sidebar.subheader("Ships")
ship_counts = {}
for ship_name in filtered_ships["Ship Name"]:
    count = st.sidebar.number_input(f"{ship_name} (PV {filtered_ships[filtered_ships['Ship Name'] == ship_name]['Cost'].values[0]})", 0, 10, 0, key=f"ship_{ship_name}")
    if count > 0:
        ship_counts[ship_name] = count

# Allow multiple of the same captain
st.sidebar.subheader("Captains")
captain_counts = {}
for captain_name in filtered_captains["Name"]:
    count = st.sidebar.number_input(f"{captain_name} (PV {filtered_captains[filtered_captains['Name'] == captain_name]['Cost'].values[0]})", 0, 10, 0, key=f"captain_{captain_name}")
    if count > 0:
        captain_counts[captain_name] = count



# Round up function
round_up = lambda x: math.ceil(x)

# Generate fighter group stats
def generate_fighter_group(fighter_names, group_type):
    subset = filtered_fighters[filtered_fighters["Fighter"].isin(fighter_names)]
    counts = pd.Series(fighter_names).value_counts()

    expanded = pd.concat([
        subset[subset["Fighter"] == name].iloc[[0]].copy().assign(count=int(count))
        for name, count in counts.items()
    ])

    # Scale stats by count
    for col in ["MAN", "DEF", "INT", "STR"]:
        expanded[col] = expanded[col] * expanded["count"]

    def compute_stat(col):
        if group_type == "Flight":
            return round_up(expanded[col].sum() / expanded["count"].sum())
        elif group_type == "Squadron":
            per_flight = max(1, int(len(fighter_names) / 3))
            flights = [fighter_names[i * per_flight:(i + 1) * per_flight] for i in range(3)]
            flight_averages = []
            for flight in flights:
                fsub = filtered_fighters[filtered_fighters["Fighter"].isin(flight)]
                c = pd.Series(flight).value_counts()
                fexp = pd.concat([
                    fsub[fsub["Fighter"] == n].iloc[[0]].copy().assign(count=cnt)
                    for n, cnt in c.items()
                ])
                fexp[col] = fexp[col] * fexp["count"]
                flight_averages.append(round_up(fexp[col].sum() / fexp["count"].sum()))
            return round_up(sum(flight_averages) / len(flight_averages))

    man = compute_stat("MAN")
    defense = compute_stat("DEF")
    intercept = compute_stat("INT")
    strafe = compute_stat("STR")
    ordnance = int((expanded["ORD"] * expanded["count"]).sum())

    qualities = ", ".join(sorted(set(q for q in expanded["Qualities"].dropna())))
    base_cost = float((expanded["COST"] * expanded["count"]).sum())
    pilot_experience_cost = experience_cost_map[experience_level] * int(expanded["count"].sum())
    total_cost = round_up(base_cost + pilot_experience_cost)

    return {
        "Type": group_type,
        "Name": fighter_group_name if fighter_group_name else f"{group_type} Group",
        "Fighters": fighter_names,
        "MAN": int(man),
        "DEF": int(defense),
        "INT": int(intercept),
        "STR": int(strafe),
        "ORD": ordnance,
        "Qualities": qualities,
        "Experience": experience_level,
        "PV": total_cost
    }

# Fighter creation method
st.sidebar.markdown("---")

with st.sidebar.expander("🛠 Fighter Group Creator", expanded=True):
    fighter_method = st.radio("Fighter Group Setup", ["Manual", "Auto by Points", "Random then Edit"])
    group_type = st.radio("Fighter Group Type", ["Flight", "Squadron"])
    fighter_group_name = st.text_input("Optional Name for Fighter Group")
    
    # Pilot Experience Level
    experience_level = st.selectbox("Pilot Experience", ["Green", "Rookie", "Regular", "Veteran", "Elite"])
    experience_cost_map = {
        "Green": 0,
        "Rookie": 1,
        "Regular": 2,
        "Veteran": 3,
        "Elite": 4
    }

    # Session state to store fighter groups
    if "fighter_groups" not in st.session_state:
        st.session_state.fighter_groups = []

    fighter_selections = []

    # Fighter selection logic
    if fighter_method == "Manual":
        max_size = 4 if group_type == "Flight" else 12
        current_total = 0
        for idx, row in filtered_fighters.iterrows():
            remaining = max_size - current_total
            if remaining <= 0:
                break
            count = st.number_input(
                f"{row['Fighter']} (PV {row['COST']})", 
                0, remaining, 0, key=f"manual_{row['Fighter']}"
            )
            if count > 0:
                fighter_selections.extend([row["Fighter"]] * count)
                current_total += count

    elif fighter_method == "Auto by Points":
        max_points = st.number_input("Max Points for Fighters", 0, 100, 10)
        size_limit = 4 if group_type == "Flight" else 12
        total = 0
        while total < max_points and len(fighter_selections) < size_limit:
            row = filtered_fighters.sample(1).iloc[0]
            if total + row["COST"] <= max_points:
                fighter_selections.append(row["Fighter"])
                total += row["COST"]

    elif fighter_method == "Random then Edit":
        size = 4 if group_type == "Flight" else 12
        for i in range(size):
            row = filtered_fighters.sample(1, replace=True).iloc[0]
            default_count = st.number_input(
                f"{row['Fighter']} (PV {row['COST']})", 
                0, size, 1, key=f"random_{i}_{row['Fighter']}_{i}"
            )
            fighter_selections.extend([row["Fighter"]] * default_count)
            if len(fighter_selections) >= size:
                fighter_selections = fighter_selections[:size]
                break

    # Add group button
    if st.button("Add Fighter Group"):
        size = len(fighter_selections)
        if group_type == "Flight" and size != 4:
            st.error("A Flight must contain exactly 4 fighters.")
        elif group_type == "Squadron" and (size < 1 or size > 12):
            st.error("A Squadron must contain between 1 and 12 fighters.")
        else:
            new_group = generate_fighter_group(fighter_selections, group_type)
            st.session_state.fighter_groups.append(new_group)
            st.success(f"{group_type} added!")





# Build force list
force = []
total_pv = 0

for name, count in ship_counts.items():
    row = filtered_ships[filtered_ships["Ship Name"] == name].iloc[0]
    for _ in range(count):
        force.append({"Type": "Ship", "Ship Name": name, "PV": row["Cost"]})
        total_pv += row["Cost"]

for name, count in captain_counts.items():
    row = filtered_captains[filtered_captains["Name"] == name].iloc[0]
    for _ in range(count):
        force.append({"Type": "Captain", "Name": name, "PV": row["Cost"]})
        total_pv += row["Cost"]

# Create a list of captains to assign
available_captains = [name for name, count in captain_counts.items() for _ in range(count)]

# Track assignments
if "ship_captain_assignments" not in st.session_state:
    st.session_state.ship_captain_assignments = {}

st.subheader("🧭 Assign Captains to Ships")

for i, entry in enumerate(force):
    if entry["Type"] == "Ship":
        ship_name = entry["Ship Name"]
        key = f"assign_captain_{i}"
        selected = st.selectbox(
            f"Captain for {ship_name} #{i + 1}",
            ["None"] + available_captains,
            key=key
        )
        st.session_state.ship_captain_assignments[key] = {
            "ship": ship_name,
            "captain": selected
        }
        
# Fighter groups with remove buttons
# Track index of group to remove
index_to_remove = None

for i, group in enumerate(st.session_state.fighter_groups):
    col1, col2 = st.columns([5, 1])
    with col1:
        st.markdown(f"**{group['Name']}** | Type: {group['Type']} | PV: {group['PV']}")
        st.markdown(f"Fighters: {', '.join(group['Fighters'])}")
        st.markdown(f"Stats – MAN: {group['MAN']}, DEF: {group['DEF']}, INT: {group['INT']}, STR: {group['STR']}, ORD: {group['ORD']}")
        st.markdown(f"Qualities: {group['Qualities']} | Experience: {group['Experience']}")
    with col2:
        if st.button("Remove", key=f"remove_{i}"):
            index_to_remove = i
    st.markdown("---")

# Apply removal outside loop
if index_to_remove is not None:
    st.session_state.fighter_groups.pop(index_to_remove)

# Append remaining fighter groups to force
for fighter_group in st.session_state.fighter_groups:
    force.append(fighter_group)
    total_pv += fighter_group["PV"]

# Main output
st.subheader("Current Force")
st.write(pd.DataFrame(force))
st.markdown(f"**Total PV: {total_pv}**")

# Convert all objects in force list to be JSON serializable
serializable_force = []
for entry in force:
    clean_entry = {k: (int(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else v) for k, v in entry.items()}
    serializable_force.append(clean_entry)

# Download buttons
st.download_button("Download JSON", data=json.dumps(serializable_force, indent=2), file_name="force.json")
st.download_button("Download CSV", data=pd.DataFrame(serializable_force).to_csv(index=False), file_name="force.csv")
