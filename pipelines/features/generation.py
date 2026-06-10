import math
from typing import Dict

# Elemental properties database for common metallic biomaterial elements
# Radius in pm (picometers), Electronegativity in Pauling scale, VEC (Valence Electron Concentration)
ELEMENTAL_DATA = {
    "Ti": {"radius": 147.0, "electronegativity": 1.54, "vec": 4, "bo": 2.870, "md": 2.447, "biocompatibility": 1.0, "atomic_weight": 47.867},
    "Nb": {"radius": 146.0, "electronegativity": 1.60, "vec": 5, "bo": 3.099, "md": 2.424, "biocompatibility": 1.0, "atomic_weight": 92.906},
    "Zr": {"radius": 160.0, "electronegativity": 1.33, "vec": 4, "bo": 3.086, "md": 2.934, "biocompatibility": 1.0, "atomic_weight": 91.224},
    "Ta": {"radius": 146.0, "electronegativity": 1.50, "vec": 5, "bo": 3.144, "md": 2.531, "biocompatibility": 1.0, "atomic_weight": 180.947},
    "Mo": {"radius": 139.0, "electronegativity": 2.16, "vec": 6, "bo": 3.061, "md": 1.961, "biocompatibility": 0.8, "atomic_weight": 95.95},
    "Fe": {"radius": 126.0, "electronegativity": 1.83, "vec": 8, "bo": 2.768, "md": 0.969, "biocompatibility": 0.6, "atomic_weight": 55.845},
    "Al": {"radius": 143.0, "electronegativity": 1.61, "vec": 3, "bo": 2.756, "md": 2.200, "biocompatibility": 0.2, "atomic_weight": 26.981},
    "V":  {"radius": 134.0, "electronegativity": 1.63, "vec": 5, "bo": 2.973, "md": 1.872, "biocompatibility": 0.0, "atomic_weight": 50.941},
    "Cr": {"radius": 128.0, "electronegativity": 1.66, "vec": 6, "bo": 2.779, "md": 1.478, "biocompatibility": 0.0, "atomic_weight": 51.996},
    "Ni": {"radius": 124.0, "electronegativity": 1.91, "vec": 8, "bo": 2.721, "md": 0.724, "biocompatibility": -0.5, "atomic_weight": 58.693},
}

# Binary liquid mixing enthalpy lookup matrix (Takeuchi and Inoue, 2005) in kJ/mol
BINARY_MIXING_ENTHALPY = {
    ("Ti", "Nb"): 2, ("Ti", "Zr"): 0, ("Ti", "Ta"): 1, ("Ti", "Mo"): -4, ("Ti", "Fe"): -17, ("Ti", "Al"): -30, ("Ti", "V"): -4, ("Ti", "Cr"): -17, ("Ti", "Ni"): -35,
    ("Nb", "Zr"): 4, ("Nb", "Ta"): 0, ("Nb", "Mo"): -6, ("Nb", "Fe"): -16, ("Nb", "Al"): -18, ("Nb", "V"): -1, ("Nb", "Cr"): -7, ("Nb", "Ni"): -30,
    ("Zr", "Ta"): 3, ("Zr", "Mo"): -6, ("Zr", "Fe"): -25, ("Zr", "Al"): -44, ("Zr", "V"): -4, ("Zr", "Cr"): -12, ("Zr", "Ni"): -49,
    ("Ta", "Mo"): -5, ("Ta", "Fe"): -15, ("Ta", "Al"): -19, ("Ta", "V"): -1, ("Ta", "Cr"): -7, ("Ta", "Ni"): -29,
    ("Mo", "Fe"): -2, ("Mo", "Al"): -5, ("Mo", "V"): 0, ("Mo", "Cr"): 0, ("Mo", "Ni"): -7,
    ("Fe", "Al"): -11, ("Fe", "V"): -7, ("Fe", "Cr"): -18, ("Fe", "Ni"): -2,
    ("Al", "V"): -16, ("Al", "Cr"): -10, ("Al", "Ni"): -22,
    ("V", "Cr"): -2, ("V", "Ni"): -20,
    ("Cr", "Ni"): -4
}

def get_binary_enthalpy(el1: str, el2: str) -> float:
    """Helper to lookup mixing enthalpy of binary pair (el1, el2) symmetrically."""
    if el1 == el2:
        return 0.0
    pair = (el1, el2)
    rev_pair = (el2, el1)
    if pair in BINARY_MIXING_ENTHALPY:
        return BINARY_MIXING_ENTHALPY[pair]
    elif rev_pair in BINARY_MIXING_ENTHALPY:
        return BINARY_MIXING_ENTHALPY[rev_pair]
    return 0.0

def convert_weight_to_atomic_fraction(composition_wt: Dict[str, float]) -> Dict[str, float]:
    """Converts a weight percentage composition to atomic fraction."""
    # Normalize weight fractions first
    total_wt = sum(composition_wt.values())
    if total_wt == 0:
        return {}
    
    moles = {}
    for el, wt in composition_wt.items():
        weight_frac = wt / total_wt
        atomic_wt = ELEMENTAL_DATA.get(el, {}).get("atomic_weight", 50.0)
        moles[el] = weight_frac / atomic_wt
        
    total_moles = sum(moles.values())
    return {el: mole / total_moles for el, mole in moles.items()}

def calculate_metallurgical_descriptors(composition_wt: Dict[str, float]) -> Dict[str, float]:
    """
    Computes metallurgical descriptors from a weight percentage alloy composition.
    
    Descriptors:
    - VEC (Valence Electron Concentration)
    - Delta (Atomic Size Mismatch)
    - Delta H mix (Mixing Enthalpy in kJ/mol)
    - Delta S mix (Mixing Entropy in J/mol*K)
    - Delta Chi (Electronegativity Difference)
    - Bo_bar (Mean Bond Order parameter)
    - Md_bar (Mean d-orbital energy level parameter in eV)
    """
    # 1. Convert to atomic fractions (c_i) for metallurgical physics equations
    c = convert_weight_to_atomic_fraction(composition_wt)
    if not c:
        return {"vec": 0, "delta": 0, "delta_h_mix": 0, "delta_s_mix": 0, "delta_chi": 0, "bo_bar": 0, "md_bar": 0}

    # 2. VEC
    vec = sum(c[el] * ELEMENTAL_DATA.get(el, {}).get("vec", 4.0) for el in c)
    
    # 3. Atomic Size Mismatch (Delta)
    r_bar = sum(c[el] * ELEMENTAL_DATA.get(el, {}).get("radius", 140.0) for el in c)
    delta = math.sqrt(sum(c[el] * (1.0 - ELEMENTAL_DATA.get(el, {}).get("radius", 140.0) / r_bar) ** 2 for el in c)) * 100.0
    
    # 4. Electronegativity Difference (Delta Chi)
    chi_bar = sum(c[el] * ELEMENTAL_DATA.get(el, {}).get("electronegativity", 1.5) for el in c)
    delta_chi = math.sqrt(sum(c[el] * (ELEMENTAL_DATA.get(el, {}).get("electronegativity", 1.5) - chi_bar) ** 2 for el in c))
    
    # 5. Mixing Entropy (Delta S mix)
    R = 8.31446  # J/(mol*K)
    delta_s_mix = -R * sum(c[el] * math.log(c[el]) for el in c if c[el] > 0)
    
    # 6. Mixing Enthalpy (Delta H mix)
    delta_h_mix = 0.0
    elements = list(c.keys())
    for i in range(len(elements)):
        for j in range(i + 1, len(elements)):
            el1, el2 = elements[i], elements[j]
            hij = get_binary_enthalpy(el1, el2)
            delta_h_mix += 4.0 * hij * c[el1] * c[el2]
            
    # 7. Bo_bar and Md_bar
    bo_bar = sum(c[el] * ELEMENTAL_DATA.get(el, {}).get("bo", 2.8) for el in c if "bo" in ELEMENTAL_DATA.get(el, {}))
    md_bar = sum(c[el] * ELEMENTAL_DATA.get(el, {}).get("md", 2.0) for el in c if "md" in ELEMENTAL_DATA.get(el, {}))

    return {
        "vec": round(vec, 4),
        "delta": round(delta, 4),
        "delta_h_mix": round(delta_h_mix, 4),
        "delta_s_mix": round(delta_s_mix, 4),
        "delta_chi": round(delta_chi, 4),
        "bo_bar": round(bo_bar, 4),
        "md_bar": round(md_bar, 4)
    }
