import json
from fastapi.testclient import TestClient
from backend.app.main import app
from pipelines.features.generation import calculate_metallurgical_descriptors

client = TestClient(app)

def test_descriptor_calculations():
    """Verify descriptor logic behaves correctly for a sample composition."""
    # Ti-35Nb-7Zr-5Ta system
    comp = {"Ti": 53.0, "Nb": 35.0, "Zr": 7.0, "Ta": 5.0}
    desc = calculate_metallurgical_descriptors(comp)
    
    assert "vec" in desc
    assert "delta" in desc
    assert "delta_h_mix" in desc
    assert desc["vec"] > 4.0 and desc["vec"] < 4.5
    assert desc["delta"] > 0.0

def test_predict_endpoint():
    """Test POST request to predictions endpoint."""
    payload = {
        "composition": {"Ti": 53.0, "Nb": 35.0, "Zr": 7.0, "Ta": 5.0},
        "model_name": "catboost"
      }
    
    response = client.post("/api/v1/predict/", json=payload)
    assert response.status_code == 200
    
    data = response.json()
    assert "predicted_properties" in data
    assert "descriptors" in data
    
    props = data["predicted_properties"]
    assert "elastic_modulus" in props
    assert "uts" in props
    assert "corrosion_rate" in props
    assert "biocompatibility_score" in props
    assert props["elastic_modulus"] > 0
