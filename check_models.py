from app import create_app
from app.models.traffic import Traffic, TrafficStats

app = create_app()

with app.app_context():
    print('Traffic模型字段:', [c.name for c in Traffic.__table__.columns])
    print('TrafficStats模型字段:', [c.name for c in TrafficStats.__table__.columns]) 