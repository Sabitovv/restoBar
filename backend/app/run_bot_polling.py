from . import bot
from .main import app


def main() -> None:
    with app.app_context():
        bot.run_polling()


if __name__ == "__main__":
    main()
