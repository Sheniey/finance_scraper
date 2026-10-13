
from datetime import datetime
from rich.console import Console
from nexis.config import MODEL_PATH, MODEL_SETTINGS_PATH
from nexis.trainer import deep_train

from scripts.ml.universe import TRAINING_UNIVERSE


console: Console = Console()

def main() -> None:
    if MODEL_PATH.exists():
        console.print(f'Size     : {MODEL_PATH.stat().st_size / 1024 / 1024:.2f} MB')

    starts_at: datetime = datetime.now()
    try:
        model, metrics, model_settings = deep_train(TRAINING_UNIVERSE)
    except KeyboardInterrupt:
        console.print('[yellow]Deep training cancelled by user.[/yellow]')
        raise SystemExit(130) from None
    ends_at: datetime = datetime.now()

    console.print(f'Deep training completed in {(ends_at - starts_at).total_seconds() / 60:.2f} minutes. Metrics:\n')
    console.print_json(metrics.model_dump_json(indent=2))
    console.print(f'\nUpdated hyperparameters saved to [green]{MODEL_SETTINGS_PATH}[/green]:')
    console.print_json(model_settings.model_dump_json(indent=2))


if __name__ == '__main__':
    main()
