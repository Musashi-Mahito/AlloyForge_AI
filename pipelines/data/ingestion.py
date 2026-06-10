import os
import random
import pandas as pd
import numpy as np
from sqlalchemy.orm import Session
from backend.app.core.database import SessionLocal, engine, Base
from backend.app.models.db_models import DBAlloy, DBProperty, DBMetallurgicalFeature
from pipelines.features.generation import calculate_metallurgical_descriptors
from pipelines.data.validation import validate_alloy_dataframe

# Set seeds for reproducibility
random.seed(42)
np.random.seed(42)

def generate_biomaterial_alloys(num_samples: int = 200) -> pd.DataFrame:
    """
    Generates a physically realistic dataset of metallic biomaterial alloys:
    1. Ti-Nb-Zr-Ta (Beta Titanium systems - highly biocompatible, low modulus)
    2. Ti-Al-V / Ti-Fe / Ti-Mo (Alpha-Beta and Alpha systems)
    3. Co-Cr-Mo (High strength, high modulus Cobalt systems)
    4. Fe-Cr-Ni-Mo (316L Stainless Steel systems)
    """
    data = []
    
    # Base alloying definitions
    all_elements = ["Ti", "Nb", "Zr", "Ta", "Mo", "Fe", "Al", "V", "Cr", "Ni"]
    
    for i in range(num_samples):
        # Pick an alloy class
        alloy_class = random.choices(
            ["beta-ti", "alpha-beta-ti", "co-cr", "ss-316l"],
            weights=[0.5, 0.2, 0.15, 0.15],
            k=1
        )[0]
        
        comp = {el: 0.0 for el in all_elements}
        name = ""
        
        if alloy_class == "beta-ti":
            # Ti-Nb-Zr-Ta system
            # High beta stabilization
            nb = random.uniform(15.0, 40.0)
            zr = random.uniform(5.0, 15.0)
            ta = random.uniform(2.0, 12.0)
            mo = random.uniform(0.0, 5.0)
            ti = 100.0 - (nb + zr + ta + mo)
            comp.update({"Ti": ti, "Nb": nb, "Zr": zr, "Ta": ta, "Mo": mo})
            
            # Physics-guided properties: Low modulus (35-80 GPa), high biocompatibility, high strength
            phase = "beta"
            modulus = 38.0 + (100.0 - ti) * 0.5 + random.normalvariate(0, 3)
            yield_strength = 500.0 + nb * 8 + ta * 5 + random.normalvariate(0, 30)
            uts = yield_strength + 100.0 + random.normalvariate(0, 15)
            # Nb, Zr, Ta are highly corrosion resistant
            corrosion = max(0.0005, 0.005 - (nb + zr + ta) * 0.0001 + random.normalvariate(0, 0.0002))
            biocompat = 0.95 + random.uniform(0.0, 0.04)
            name = f"Ti-{nb:.1f}Nb-{zr:.1f}Zr-{ta:.1f}Ta-{i+1}"
            
        elif alloy_class == "alpha-beta-ti":
            # Ti-Al-V / Ti-Fe / Ti-Cr system
            # Moderate stabilization, contains toxic Al/V
            al = random.uniform(4.0, 8.0)
            v = random.uniform(2.0, 6.0)
            fe = random.uniform(0.0, 2.0)
            ti = 100.0 - (al + v + fe)
            comp.update({"Ti": ti, "Al": al, "V": v, "Fe": fe})
            
            phase = "alpha-beta"
            modulus = 105.0 + al * 1.5 - v * 0.8 + random.normalvariate(0, 4)
            yield_strength = 750.0 + al * 25 + v * 15 + random.normalvariate(0, 40)
            uts = yield_strength + 120.0 + random.normalvariate(0, 20)
            corrosion = 0.008 + random.normalvariate(0, 0.001)
            biocompat = 0.45 + random.uniform(0.0, 0.1) # low due to Al/V
            name = f"Ti-{al:.1f}Al-{v:.1f}V-{i+1}"
            
        elif alloy_class == "co-cr":
            # Co-Cr-Mo (Cobalt-Chromium-Molybdenum) base.
            # In our list, we don't have Co or Cr fully representing the 60% Co base, 
            # let's assume we represent this via Ni/Cr/Mo/Fe, or we model Co-Cr directly.
            # To stay within our elements, let's treat "Ti" as cobalt/base for calculation
            # or simplify: Co-Cr-Mo can be approximated by Cr (28%), Mo (6%), Ni (2%), Fe (1%), base (Co) is represented by Ni/Fe
            # Let's say Ni is the base here (40-60%) to make VEC, size etc. realistic
            ni = random.uniform(50.0, 65.0)
            cr = random.uniform(26.0, 30.0)
            mo = random.uniform(5.0, 7.0)
            fe = 100.0 - (ni + cr + mo)
            comp.update({"Ni": ni, "Cr": cr, "Mo": mo, "Fe": fe})
            
            phase = "fcc"
            modulus = 210.0 + random.normalvariate(0, 10)
            yield_strength = 450.0 + cr * 12 + mo * 20 + random.normalvariate(0, 35)
            uts = yield_strength + 300.0 + random.normalvariate(0, 50)
            corrosion = 0.015 + random.normalvariate(0, 0.002)
            biocompat = 0.65 + random.uniform(0.0, 0.05) # Ni/Cr are semi-sensitizing
            name = f"Ni-{cr:.1f}Cr-{mo:.1f}Mo-{i+1}"
            
        else: # ss-316l
            # Fe-Cr-Ni-Mo Stainless steel
            cr = random.uniform(16.0, 18.0)
            ni = random.uniform(10.0, 14.0)
            mo = random.uniform(2.0, 3.0)
            fe = 100.0 - (cr + ni + mo)
            comp.update({"Fe": fe, "Cr": cr, "Ni": ni, "Mo": mo})
            
            phase = "austenite"
            modulus = 193.0 + random.normalvariate(0, 5)
            yield_strength = 200.0 + mo * 30 + random.normalvariate(0, 15)
            uts = yield_strength + 300.0 + random.normalvariate(0, 30)
            corrosion = 0.025 + random.normalvariate(0, 0.004)
            biocompat = 0.55 + random.uniform(0.0, 0.05) # Ni content lowers score
            name = f"Fe-{cr:.1f}Cr-{ni:.1f}Ni-{mo:.1f}Mo-{i+1}"
            
        # Calculate descriptors
        desc = calculate_metallurgical_descriptors(comp)
        
        # Merge dictionaries
        row = {
            "name": name,
            "phase": phase,
            "elastic_modulus": float(modulus),
            "yield_strength": float(yield_strength),
            "uts": float(uts),
            "corrosion_rate": float(corrosion),
            "biocompatibility_score": float(biocompat)
        }
        row.update(comp)
        row.update(desc)
        data.append(row)
        
    df = pd.DataFrame(data)
    
    # Enforce constraints and validate
    df = validate_alloy_dataframe(df)
    return df

def seed_database(df: pd.DataFrame):
    """Populates the database with the generated DataFrame rows."""
    # Ensure tables are created
    Base.metadata.create_all(bind=engine)
    
    db: Session = SessionLocal()
    try:
        # Check if database is already seeded
        if db.query(DBAlloy).count() > 0:
            print("Database already seeded. Skipping seeder.")
            return
            
        print(f"Seeding {len(df)} alloys into SQL database...")
        for _, row in df.iterrows():
            comp_dict = {
                el: float(row[el]) 
                for el in ["Ti", "Nb", "Zr", "Ta", "Mo", "Fe", "Al", "V", "Cr", "Ni"] 
                if row[el] > 0
            }
            
            db_alloy = DBAlloy(
                name=row["name"],
                composition=comp_dict,
                phase=row["phase"]
            )
            db.add(db_alloy)
            db.flush()  # Gets the alloy ID
            
            db_properties = DBProperty(
                alloy_id=db_alloy.id,
                elastic_modulus=row["elastic_modulus"],
                yield_strength=row["yield_strength"],
                uts=row["uts"],
                corrosion_rate=row["corrosion_rate"],
                biocompatibility_score=row["biocompatibility_score"],
                is_experimental=True
            )
            
            db_features = DBMetallurgicalFeature(
                alloy_id=db_alloy.id,
                vec=row["vec"],
                delta=row["delta"],
                delta_h_mix=row["delta_h_mix"],
                delta_s_mix=row["delta_s_mix"],
                delta_chi=row["delta_chi"],
                bo_bar=row["bo_bar"],
                md_bar=row["md_bar"]
            )
            
            db.add(db_properties)
            db.add(db_features)
            
        db.commit()
        print("Database successfully seeded.")
    except Exception as e:
        db.rollback()
        print(f"Error seeding database: {e}")
        raise e
    finally:
        db.close()

if __name__ == "__main__":
    # Ensure local folders exist
    os.makedirs("data/raw", exist_ok=True)
    
    # 1. Generate realistic data
    print("Generating alloy datasets...")
    df = generate_biomaterial_alloys(num_samples=200)
    
    # 2. Save versioned Parquet file
    parquet_path = "data/raw/alloy_dataset.parquet"
    df.to_parquet(parquet_path, index=False)
    print(f"Saved dataset to Parquet file: {parquet_path}")
    
    # 3. Seed SQL Database
    seed_database(df)
