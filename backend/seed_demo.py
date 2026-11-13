"""Seed demo gym/users matching the frontend login presets. Idempotent."""
from app.core.security import get_password_hash
from app.db.session import SessionLocal
from app.models.core import Branch, Gym, Role, User, UserRole

DEMO_USERS = [
    ("owner@example.com", "Owner", "owner", None),
    ("admin@example.com", "Admin", "admin", 1),
    ("reception@example.com", "Reception", "reception", 1),
    ("trainer@example.com", "Trainer", "trainer", 1),
]

ROLE_NAMES = ["owner", "admin", "reception", "trainer"]


def main() -> None:
    db = SessionLocal()
    try:
        gym = db.query(Gym).filter(Gym.gym_id == 1).first()
        if gym is None:
            gym = Gym(gym_id=1, branch_id=None, name="Demo Gym", webhook_token="demo-gym1")
            db.add(gym)
            db.flush()
        branch = db.query(Branch).filter(Branch.gym_id == gym.id, Branch.branch_id == 1).first()
        if branch is None:
            branch = Branch(gym_id=gym.id, branch_id=1, name="Main Branch")
            db.add(branch)
            db.flush()

        roles: dict[str, Role] = {}
        for name in ROLE_NAMES:
            r = db.query(Role).filter(Role.gym_id == gym.id, Role.name == name).first()
            if r is None:
                r = Role(gym_id=gym.id, branch_id=branch.id, name=name)
                db.add(r)
                db.flush()
            roles[name] = r

        pw = get_password_hash("secret123")
        for email, full_name, role_name, branch_id in DEMO_USERS:
            user = db.query(User).filter(User.gym_id == gym.id, User.email == email).first()
            if user is None:
                user = User(
                    gym_id=gym.id,
                    branch_id=branch_id,
                    email=email,
                    full_name=full_name,
                    hashed_password=pw,
                    is_active=True,
                )
                db.add(user)
                db.flush()
            if db.query(UserRole).filter(UserRole.user_id == user.id, UserRole.role_id == roles[role_name].id).first() is None:
                db.add(UserRole(gym_id=gym.id, branch_id=branch_id, user_id=user.id, role_id=roles[role_name].id))

        db.commit()
        print(f"seeded gym_id={gym.id} users={len(DEMO_USERS)}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
