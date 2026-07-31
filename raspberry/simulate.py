import argparse
from datetime import datetime, timezone
from uuid import uuid4

from raspberry.api_client import RePointsApiClient
from raspberry.bottle_classifier import SimulatedBottleClassifier
from raspberry.config import RaspberryConfig


def run() -> None:
    parser = argparse.ArgumentParser(description="Simula una botella sin usar cámaras")
    parser.add_argument("--qr-token", required=True)
    parser.add_argument("--material", choices=("plastic", "glass"), default="plastic")
    parser.add_argument("--confidence", type=float, default=0.95)
    args = parser.parse_args()
    config = RaspberryConfig.from_environment()
    classifier = SimulatedBottleClassifier(args.material, args.confidence)
    client = RePointsApiClient(config.api_base_url, config.device_code, config.device_api_key)
    validation = client.validate_user(args.qr_token)
    result = classifier.classify()
    response = client.register_bottle(
        str(uuid4()),
        args.qr_token,
        result.material,
        result.confidence,
        datetime.now(timezone.utc),
    )
    print(f"Usuario: {validation['user']['name']}")
    print(response["message"])
    print(f"+{response['tokensEarned']} puntos; saldo local: {response['localBalance']}")


if __name__ == "__main__":
    run()
