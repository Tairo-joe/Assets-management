from app import create_app, db
from app.models import User


def upsert_user(username: str, email: str, role: str, password: str) -> None:
    user = User.query.filter_by(username=username).first()
    if user is None:
        user = User(username=username, email=email, role=role)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        print(f"CREATED {username} role={role} email={email}")
    else:
        user.email = email
        user.role = role
        user.set_password(password)
        db.session.commit()
        print(f"UPDATED {username} role={role} email={email}")


def main() -> None:
    app = create_app()
    with app.app_context():
        upsert_user("admin", "admin@example.com", "Admin", "ChangeMe123!")
        upsert_user("it", "it@example.com", "IT", "ChangeMe123!")
        print("Done.")


if __name__ == "__main__":
    main()


