from __future__ import annotations

import argparse
from dotenv import load_dotenv

load_dotenv()

from app.main import create_app
from app.extensions import db
from app.models import MembershipStatus, Restaurant, StaffMembership, StaffRole


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create or update active super admin membership.")
    parser.add_argument("--telegram-user-id", type=int, required=True)
    parser.add_argument("--username", type=str, default=None)
    parser.add_argument("--restaurant-slug", type=str, default="main")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    app = create_app()
    with app.app_context():
        restaurant = Restaurant.query.filter_by(slug=args.restaurant_slug).first()
        if restaurant is None:
            raise SystemExit(f"Restaurant with slug '{args.restaurant_slug}' not found")

        membership = StaffMembership.query.filter_by(
            restaurant_id=restaurant.id,
            telegram_user_id=args.telegram_user_id,
        ).first()

        if membership is None:
            membership = StaffMembership(
                restaurant_id=restaurant.id,
                telegram_user_id=args.telegram_user_id,
                username=args.username,
                role=StaffRole.super_admin,
                status=MembershipStatus.active,
            )
            db.session.add(membership)
        else:
            membership.username = args.username
            membership.role = StaffRole.super_admin
            membership.status = MembershipStatus.active

        db.session.commit()
        print(f"Super admin is active for telegram_user_id={args.telegram_user_id} in restaurant='{args.restaurant_slug}'")


if __name__ == "__main__":
    main()
