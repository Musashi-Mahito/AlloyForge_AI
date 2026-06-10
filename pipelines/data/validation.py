import pandera as pa
from pandera import Column, Check, DataFrameSchema

# Schema for validation during ingestion / training
AlloyTrainingSchema = DataFrameSchema(
    columns={
        "name": Column(str, required=True),
        # Compositions are stored as floats, between 0.0 and 100.0 (wt. %)
        "Ti": Column(float, Check.in_range(0.0, 100.0), nullable=True),
        "Nb": Column(float, Check.in_range(0.0, 100.0), nullable=True),
        "Zr": Column(float, Check.in_range(0.0, 100.0), nullable=True),
        "Ta": Column(float, Check.in_range(0.0, 100.0), nullable=True),
        "Mo": Column(float, Check.in_range(0.0, 100.0), nullable=True),
        "Fe": Column(float, Check.in_range(0.0, 100.0), nullable=True),
        "Al": Column(float, Check.in_range(0.0, 100.0), nullable=True),
        "V": Column(float, Check.in_range(0.0, 100.0), nullable=True),
        "Cr": Column(float, Check.in_range(0.0, 100.0), nullable=True),
        "Ni": Column(float, Check.in_range(0.0, 100.0), nullable=True),
        
        # Descriptors
        "vec": Column(float, Check.in_range(2.0, 10.0)),
        "delta": Column(float, Check.in_range(0.0, 30.0)), # size mismatch %
        "delta_h_mix": Column(float, Check.in_range(-100.0, 50.0)),
        "delta_s_mix": Column(float, Check.in_range(0.0, 30.0)),
        "delta_chi": Column(float, Check.in_range(0.0, 5.0)),
        
        # Target properties
        "elastic_modulus": Column(float, Check.in_range(5.0, 300.0)), # GPa
        "yield_strength": Column(float, Check.in_range(50.0, 3000.0)), # MPa
        "uts": Column(float, Check.in_range(100.0, 4000.0)), # MPa
        "corrosion_rate": Column(float, Check.greater_than_or_equal_to(0.0)), # mm/year
        "biocompatibility_score": Column(float, Check.in_range(0.0, 1.0))
    },
    # Ensure columns representing weights sum to roughly 100%
    checks=[
        Check(
            lambda df: (df[["Ti", "Nb", "Zr", "Ta", "Mo", "Fe", "Al", "V", "Cr", "Ni"]].fillna(0.0).sum(axis=1) - 100.0).abs() < 1e-2,
            name="check_wt_percent_sum_100"
        )
    ],
    coerce=True
)

def validate_alloy_dataframe(df):
    """Validates pandas DataFrame against physical constraints and schema rules."""
    return AlloyTrainingSchema.validate(df)
