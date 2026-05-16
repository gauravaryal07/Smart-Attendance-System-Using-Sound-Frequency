from app import app
from database import db, User

def add_multiple_students():
    # List of (ID, Username, Full Name, Password)
    new_students = [
        (102, "rahul", "Rahul Verma", "pass123"),
        (103, "priya", "Priya Sharma", "pass123"),
        (104, "amit", "Amit Kumar", "pass123"),
        (105,"gavi","Gavisiddheshwor","pass123"),
        (106,"dakshit","Dakshit c","pass123"),
        (107,"deekshya","Deekshya","pass123"),
        (108,"bikalpa","Bikalpa Lamsal","pass123"),
    ]

    with app.app_context():
        for s_id, uname, name, pwd in new_students:
            # Check if user already exists
            if not User.query.filter_by(username=uname).first():
                user = User(id=s_id, username=uname, name=name)
                user.set_password(pwd) # This encrypts it!
                db.session.add(user)
                print(f"Added: {name}")
        
        db.session.commit()
        print("--- All students added successfully ---")

if __name__ == "__main__":
    add_multiple_students()