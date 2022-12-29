from flask import request, jsonify
from flask_jwt_extended import create_access_token, get_jwt

from util import *
from auth import student_auth, coordinator_auth, admin_auth
from init import app, jwt, bcrypt, db

#=======================================================================================================
#=======================================  GENERAL  =====================================================

@app.route("/all-departments", methods=['GET'])
def all_departments():
    try:
        departments = db.fetch("SELECT * FROM department")
        return {"departments": departments}, 200
    except Exception as e:
        print(e)
        return {"message": "An error occured"}, 500

@app.route("/all-coordinators", methods=['GET'])
def all_coordinators():
    try:
        coordinators = db.fetch("SELECT id, name FROM coordinator")
        return {"coordinators": coordinators}, 200
    except Exception as e:
        print(e)
        return {"message": "An error occured"}, 500

#=======================================================================================================
#=======================================  STUDENT  =====================================================

@app.route("/student/register", methods=['POST'])
def student_register():

        data = request.get_json()
        student_no = data['student_no']
        name = data['name']
        surname = data['surname']
        email = data['email']
        password = data['password']
        department_id = data['department_id']

        student = db.fetch_one("SELECT * FROM student WHERE student_no = %s LIMIT 1", (student_no,))
        if student:
            return {"message": "Student already exists"}, 400

        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        db.execute("INSERT INTO student (student_no, name, surname, email, password, department_id) VALUES (%s, %s, %s, %s, %s, %s)", (student_no, name, surname, email, hashed_password, department_id))
        return {"message": "Student created successfully"}, 200


@app.route("/student/login", methods=['POST'])
def student_login():
    try:
        data = request.get_json()
        student_no = data['student_no']
        password = data['password']

        student = db.fetch_one("SELECT * FROM student WHERE student_no = %s LIMIT 1", (student_no,))
        if not student:
            return {"message": "Invalid credentials"}, 401

        if not bcrypt.check_password_hash(student['password'], password):
            return {"message": "Invalid credentials"}, 401

        token_identity = {
            'type': 'student',
            'id': student['id']
        }

        access_token = create_access_token(identity=token_identity)
        return {"access_token": access_token}, 200
    except Exception as e:
        print(e)
        return {"message": "An error occured"}, 500

@app.route("/student/courses", methods=['GET'])
@student_auth()
def student_courses():
    try:
        student_id = get_jwt()['sub']['id']
        student = db.fetch_one("SELECT * FROM student WHERE id = %s LIMIT 1", (student_id,))

        if not student:
            return {"message": "Student not found"}, 404

        courses = db.fetch(
            """SELECT id, name, course_code
               FROM MEFcourse
               WHERE department_id = %s and is_active = True
            """,
            (student['department_id'],)
        )
        return {"courses": courses}, 200
    except Exception as e:
        print(e)
        return {"message": "An error occured"}, 500

@app.route("/student/enroll", methods=['POST'])
@student_auth()
def student_enroll():
    try:
        data = request.get_json()
        student_id = get_jwt()['sub']['id']
        course_id = data['course_id']

        student = db.fetch_one("SELECT * FROM student WHERE id = %s LIMIT 1", (student_id,))
        if not student:
            return {"message": "Student not found"}, 404

        course = db.fetch_one("SELECT * FROM MEFcourse WHERE id = %s and is_active = True LIMIT 1", (course_id,))
        if not course:
            return {"message": "Course not found"}, 404

        if course['department_id'] != student['department_id']:
            return {"message": "You cannot enroll in this course"}, 400

        db.execute("INSERT INTO enrollment (student_id, course_id) VALUES (%s, %s)", (student_id, course_id))
        return {"message": "Enrolled successfully"}, 200
    except Exception as e:
        print(e)
        return {"message": "An error occured"}, 500

@app.route("/student/enrollments", methods=['GET'])
@student_auth()
def student_enrollments():
    try:
        student_id = get_jwt()['sub']['id']
        student = db.fetch_one("SELECT * FROM student WHERE id = %s LIMIT 1", (student_id,))

        if not student:
            return {"message": "Student not found"}, 404

        enrollments = db.fetch(
            """SELECT e.id as enrolment_id, c.id as course_id, c.name, c.course_code
               FROM enrollment e
               INNER JOIN MEFcourse c ON c.id = e.course_id
               WHERE e.student_id = %s and c.is_active = True
            """,
            (student_id,)
        )
        return {"enrollments": enrollments}, 200
    except Exception as e:
        print(e)
        return {"message": "An error occured"}, 500

@app.route("/student/enrollments/<int:course_id>/bundles", methods=['GET'])
@student_auth()
def student_enrollment_bundles(course_id):
    try:
        student_id = get_jwt()['sub']['id']
        student = db.fetch_one("SELECT * FROM student WHERE id = %s LIMIT 1", (student_id,))

        if not student:
            return {"message": "Student not found"}, 404

        course = db.fetch_one("SELECT * FROM MEFcourse WHERE id = %s and is_active = True LIMIT 1", (course_id,))
        if not course:
            return {"message": "Course not found"}, 404

        if course['department_id'] != student['department_id']:
            return {"message": "You cannot view this course"}, 400

        enrollment = db.fetch_one("SELECT * FROM enrollment WHERE student_id = %s and course_id = %s LIMIT 1", (student_id, course_id))
        if not enrollment:
            return {"message": "You are not enrolled in this course"}, 400

        bundles = db.fetch(
            """SELECT b.id as bundle_id, b.created_at, b.status as bundle_status, m.name, m.url
               FROM bundle b
               INNER JOIN bundle_detail bd ON bd.bundle_id = b.id
               INNER JOIN mooc m ON m.id = bd.mooc_id
               WHERE b.enrollment_id = %s
            """,
            (enrollment["id"],)
        )
        return {"bundles": bundles}, 200
    except Exception as e:
        print(e)
        return {"message": "An error occured"}, 500

@app.route("/student/moocs", methods=['GET'])
@student_auth()
def student_moocs():
    try:
        student_id = get_jwt()['sub']['id']
        student = db.fetch_one("SELECT * FROM student WHERE id = %s LIMIT 1", (student_id,))

        if not student:
            return {"message": "Student not found"}, 404

        moocs = db.fetch("SELECT * FROM mooc WHERE is_active = True")
        return {"moocs": moocs}, 200
    except Exception as e:
        print(e)
        return {"message": "An error occured"}, 500

@app.route("/student/enrollments/<int:course_id>/create-bundle", methods=['POST'])
@student_auth()
def student_create_bundle(course_id):
    try:
        student_id = get_jwt()['sub']['id']
        student = db.fetch_one("SELECT * FROM student WHERE id = %s LIMIT 1", (student_id,))

        if not student:
            return {"message": "Student not found"}, 404

        course = db.fetch_one("SELECT * FROM MEFcourse WHERE id = %s and is_active = True LIMIT 1", (course_id,))
        if not course:
            return {"message": "Course not found"}, 404

        if course['department_id'] != student['department_id']:
            return {"message": "You cannot view this course"}, 400

        enrollment = db.fetch_one("SELECT * FROM enrollment WHERE student_id = %s and course_id = %s LIMIT 1", (student_id, course_id))
        if not enrollment:
            return {"message": "You are not enrolled in this course"}, 400

        bundles = db.fetch(
            """
            SELECT * FROM bundle WHERE enrollment_id = %s
                                 AND (status = 'Waiting Bundles' OR status = 'Waiting Certificates'
                                 OR status = 'Rejected Certificates' OR status = 'Accepted Certificates')
            """,
            (enrollment["id"],)
        )
        if len(bundles) != 0:
            return {"message": "You cannot create a new bundle because you have waiting or accepting bundles"}, 400

        data = request.get_json()
        mooc_ids = data['mooc_ids']

        moocs = db.fetch("SELECT * FROM mooc WHERE id IN %s and is_active = True", (tuple(mooc_ids),))
        if len(moocs) != len(mooc_ids):
            return {"message": "Invalid mooc ids"}, 400
        
        try:
            bundle = db.execute("INSERT INTO bundle (enrollment_id) VALUES (%s)", (enrollment['id'],))
            bundle_id = db.fetch_one("SELECT id FROM bundle WHERE enrollment_id = %s ORDER BY id DESC LIMIT 1", (enrollment['id'],))["id"]
            for mooc in mooc_ids:
                db.execute("INSERT INTO bundle_detail (bundle_id, mooc_id) VALUES (%s, %s)", (bundle_id, mooc))

        # TODO: ROllback
        except Exception as e:
            print(e)
            return {"message": "An error occured"}, 500

        return {"message": "Bundle created successfully"}, 200
    except Exception as e:
        print(e)
        return {"message": "An error occured"}, 500

@app.route("/student/enrollments/<int:course_id>/bundles/<int:bundle_id>", methods=['GET'])
@student_auth()
def student_bundle(course_id, bundle_id):
    try:
        student_id = get_jwt()['sub']['id']
        student = db.fetch_one("SELECT * FROM student WHERE id = %s LIMIT 1", (student_id,))

        if not student:
            return {"message": "Student not found"}, 404

        course = db.fetch_one("SELECT * FROM MEFcourse WHERE id = %s and is_active = True LIMIT 1", (course_id,))
        if not course:
            return {"message": "Course not found"}, 404

        if course['department_id'] != student['department_id']:
            return {"message": "You cannot view this course"}, 400

        enrollment = db.fetch_one("SELECT * FROM enrollment WHERE student_id = %s and course_id = %s LIMIT 1", (student_id, course_id))
        if not enrollment:
            return {"message": "You are not enrolled in this course"}, 400

        bundles = db.fetch(
            """
            SELECT bd.id as bundle_detail_id, m.id as mooc_id, m.name as mooc_name
            FROM bundle_detail bd
            INNER JOIN mooc m ON m.id = bd.mooc_id
            WHERE bd.bundle_id = %s
            """,
            (bundle_id,)
        )
        return {"bundle": bundles}, 200
    except Exception as e:
        print(e)
        return {"message": "An error occured"}, 500

@app.route("/student/enrollments/<int:course_id>/bundles/<int:bundle_id>/certificate", methods=['POST'])
@student_auth()
def student_create_certificate(course_id, bundle_id):
    try:
        student_id = get_jwt()['sub']['id']
        student = db.fetch_one("SELECT * FROM student WHERE id = %s LIMIT 1", (student_id,))

        if not student:
            return {"message": "Student not found"}, 404

        course = db.fetch_one("SELECT * FROM MEFcourse WHERE id = %s and is_active = True LIMIT 1", (course_id,))
        if not course:
            return {"message": "Course not found"}, 404

        if course['department_id'] != student['department_id']:
            return {"message": "You cannot view this course"}, 400

        enrollment = db.fetch_one("SELECT * FROM enrollment WHERE student_id = %s and course_id = %s LIMIT 1", (student_id, course_id))
        if not enrollment:
            return {"message": "You are not enrolled in this course"}, 400

        bundle = db.fetch_one("SELECT * FROM bundle WHERE id = %s and enrollment_id = %s LIMIT 1", (bundle_id, enrollment['id']))
        if not bundle:
            return {"message": "Bundle not found"}, 404

        if bundle['status'] != 'Waiting Certificates':
            return {"message": "You cannot upload certificates for this bundle"}, 400

        data = request.get_json()
        certificate_url = data['certificate_url']
        bundle_detail_id = data['bundle_detail_id']

        db.execute("UPDATE bundle_detail SET certificate_url = %s WHERE id = %s", (certificate_url, bundle_detail_id))

        return {"message": "Certificate created successfully"}, 200
    except Exception as e:
        print(e)
        return {"message": "An error occured"}, 500

@app.route("/student/enrollments/<int:course_id>/bundles/<int:bundle_id>/complete", methods=['POST'])
@student_auth()
def student_complete_bundle(course_id, bundle_id):
    try:
        student_id = get_jwt()['sub']['id']
        student = db.fetch_one("SELECT * FROM student WHERE id = %s LIMIT 1", (student_id,))

        if not student:
            return {"message": "Student not found"}, 404

        course = db.fetch_one("SELECT * FROM MEFcourse WHERE id = %s and is_active = True LIMIT 1", (course_id,))
        if not course:
            return {"message": "Course not found"}, 404

        if course['department_id'] != student['department_id']:
            return {"message": "You cannot view this course"}, 400

        enrollment = db.fetch_one("SELECT * FROM enrollment WHERE student_id = %s and course_id = %s LIMIT 1", (student_id, course_id))
        if not enrollment:
            return {"message": "You are not enrolled in this course"}, 400

        bundle = db.fetch_one("SELECT * FROM bundle WHERE id = %s and enrollment_id = %s LIMIT 1", (bundle_id, enrollment['id']))
        if not bundle:
            return {"message": "Bundle not found"}, 404

        if bundle['status'] != 'Waiting Certificates':
            return {"message": "You cannot complete this bundle"}, 400

        bundle_details = db.fetch("SELECT * FROM bundle_detail WHERE bundle_id = %s", (bundle_id,))
        for bundle_detail in bundle_details:
            if not bundle_detail['certificate_url']:
                return {"message": "You cannot complete this bundle"}, 400

        db.execute("UPDATE bundle SET status = 'Waiting Certificates' WHERE id = %s", (bundle_id,))

        return {"message": "Bundle completed successfully"}, 200
    except Exception as e:
        print(e)
        return {"message": "An error occured"}, 500

#=======================================================================================================
#========================================== COORDINATOR ================================================

@app.route("/coordinator/login", methods=['POST'])
def coordinator_login():
    try:
        data = request.get_json()
        email = data['email']
        password = data['password']

        coordinator = db.fetch_one("SELECT * FROM coordinator WHERE email = %s LIMIT 1", (email,))
        if not coordinator:
            return {"message": "Invalid credentials"}, 401

        if not bcrypt.check_password_hash(coordinator['password'], password):
            return {"message": "Invalid credentials"}, 401

        token_identity = {
            'type': 'coordinator',
            'id': coordinator['id']
        }

        access_token = create_access_token(identity=token_identity)
        return {"access_token": access_token}, 200
    except Exception as e:
        print(e)
        return {"message": "An error occured"}, 500

#=======================================================================================================
#========================================== ADMIN ======================================================

@app.route("/admin/login", methods=['POST'])
def admin_login():
    try:
        data = request.get_json()
        username = data['username']
        password = data['password']

        if username != app.config['ADMIN_USERNAME'] or password != app.config['ADMIN_PASSWORD']:
            return {"message": "Invalid credentials"}, 401

        token_identity = {
            'type': 'admin',
            'id': 1
        }

        access_token = create_access_token(identity=token_identity)
        return {"access_token": access_token}, 200
    except Exception as e:
        print(e)
        return {"message": "An error occured"}, 500


@app.route("/student/create-bundle", methods=['GET'])
@student_auth()
def create_bundle():
    return "Selamlar"

if __name__ == "__main__":
    app.run(debug=True)