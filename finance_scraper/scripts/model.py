
from typer import Typer, Option, Argument
from typing import Annotated

from nexis.scripts.deep_training import main as deep_training
from nexis.scripts.training import main as training


app: Typer = Typer()

@app.command(
    name='train',
    help='Run the training script'
)
def Training(
        deep: Annotated[
            bool,
            Option(
                help='It runs a training process that continuously self-adjusts the predictive model\'s ' +
                'hyperparameters until an optimal configuration is reached.'
            )
        ] = False
    ) -> None:
    if deep:
        deep_training()
    else:
        training()


if __name__ == '__main__':
    app()
