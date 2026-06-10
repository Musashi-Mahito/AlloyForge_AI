from sqlalchemy import Column, Integer, String, Float, ForeignKey, Boolean, DateTime, JSON
from sqlalchemy.orm import relationship
import datetime
from backend.app.core.database import Base

class DBAlloy(Base):
    __tablename__ = "alloys"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, index=True, nullable=False)
    composition = Column(JSON, nullable=False)  # Dict mapping elements to weight/atomic fractions (e.g., {"Ti": 0.65, "Nb": 0.25, "Zr": 0.05, "Ta": 0.05})
    phase = Column(String(50), nullable=True)     # Crystal phase stability indicator (e.g. "beta", "alpha-beta")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Relationships
    properties = relationship("DBProperty", back_populates="alloy", cascade="all, delete-orphan")
    features = relationship("DBMetallurgicalFeature", back_populates="alloy", cascade="all, delete-orphan")

class DBProperty(Base):
    __tablename__ = "properties"

    id = Column(Integer, primary_key=True, index=True)
    alloy_id = Column(Integer, ForeignKey("alloys.id", ondelete="CASCADE"), nullable=False)
    elastic_modulus = Column(Float, nullable=False)  # GPa
    yield_strength = Column(Float, nullable=False)   # MPa
    uts = Column(Float, nullable=False)              # MPa
    corrosion_rate = Column(Float, nullable=False)   # mm/year
    biocompatibility_score = Column(Float, nullable=False)
    is_experimental = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    alloy = relationship("DBAlloy", back_populates="properties")

class DBMetallurgicalFeature(Base):
    __tablename__ = "metallurgical_features"

    id = Column(Integer, primary_key=True, index=True)
    alloy_id = Column(Integer, ForeignKey("alloys.id", ondelete="CASCADE"), nullable=False)
    vec = Column(Float, nullable=False)            # Valence Electron Concentration
    delta = Column(Float, nullable=False)          # Atomic size mismatch (%)
    delta_h_mix = Column(Float, nullable=False)    # Enthalpy of mixing (kJ/mol)
    delta_s_mix = Column(Float, nullable=False)    # Entropy of mixing (J/mol*K)
    delta_chi = Column(Float, nullable=False)      # Electronegativity difference
    bo_bar = Column(Float, nullable=True)          # Mean bond order
    md_bar = Column(Float, nullable=True)          # Mean d-orbital energy level

    alloy = relationship("DBAlloy", back_populates="features")

class DBOptimizationRun(Base):
    __tablename__ = "optimization_runs"

    id = Column(String(36), primary_key=True, index=True) # UUID representation
    objectives = Column(JSON, nullable=False)            # Targets and weights
    algorithm = Column(String(50), nullable=False)
    runtime_seconds = Column(Float, nullable=True)
    candidates_generated = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
