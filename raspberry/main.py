import time

from raspberry.api_client import RePointsApiClient
from raspberry.ai.expert_system import ExpertRules
from raspberry.ai.inference import MockBottleClassifier, TFLiteBottleClassifier
from raspberry.ai.pending_queue import PendingEventQueue
from raspberry.camera_manager import DualCameraManager
from raspberry.config import RaspberryConfig
from raspberry.qr_reader import QrReader
from raspberry.state_machine import RecyclingStation, StationState


def run() -> None:
    config = RaspberryConfig.from_environment()
    rules = ExpertRules(config.ai_accept_threshold, config.ai_recapture_threshold)
    classifier = (
        MockBottleClassifier("plastic", 0.95, config.ai_model_version, rules, config.ai_mock_mode)
        if config.ai_mock_mode
        else TFLiteBottleClassifier(config.ai_model_path, config.ai_labels_path, config.ai_model_version, rules)
    )
    client = RePointsApiClient(
        config.api_base_url,
        config.device_code,
        config.device_api_key,
        config.request_timeout_seconds,
        config.request_max_retries,
        PendingEventQueue(config.pending_events_path),
    )
    client.flush_pending()
    station = RecyclingStation(
        QrReader(),
        classifier,
        client,
        config.ai_accept_threshold,
        config.ai_recapture_threshold,
    )
    try:
        import cv2
        with DualCameraManager(config.qr_camera_index, config.bottle_camera_index) as cameras:
            print("Estación iniciada. Presiona Q para salir y R para reiniciar.")
            while True:
                qr_frame = cameras.read_qr_frame()
                bottle_frame = cameras.read_bottle_frame()
                if station.snapshot.state == StationState.WAITING_QR:
                    station.process_qr_frame(qr_frame)
                elif station.snapshot.state == StationState.WAITING_BOTTLE:
                    station.process_bottle_frame(bottle_frame)

                print(f"\r{station.snapshot.state.value}: {station.snapshot.message}", end="", flush=True)
                if not config.headless:
                    cv2.imshow("Re-Points QR", qr_frame)
                    cv2.imshow("Re-Points Botella", bottle_frame)
                    key = cv2.waitKey(1) & 0xFF
                    if key == ord("q"):
                        break
                    if key == ord("r"):
                        station.reset()
                if station.snapshot.state in {StationState.SUCCESS, StationState.ERROR}:
                    time.sleep(3)
                    station.reset()
    finally:
        if not config.headless:
            cv2.destroyAllWindows()


if __name__ == "__main__":
    run()
