import tkinter as tk
from tkinter import messagebox
import pymysql
import cv2
import numpy as np
from PIL import Image, ImageTk
import pyttsx3 as pr
from datetime import datetime
import time
import os

# Database connection
def insertupdater(Id, Name, age):
    mydb = pymysql.connect(host="localhost", user="root", passwd="aditya2808", database="college")
    conn = mydb.cursor()

    cmd = "SELECT * FROM STUDENT WHERE ID = %s"
    conn.execute(cmd, (Id,))
    isrecordexist = conn.fetchone()  # fetch one record

    if isrecordexist:
        conn.execute("UPDATE STUDENT SET NAME = %s, AGE = %s WHERE ID = %s", (Name, age, Id))
    else:
        conn.execute("INSERT INTO STUDENT (ID, NAME, AGE) VALUES (%s, %s, %s)", (Id, Name, age))

    mydb.commit()
    conn.close()
    mydb.close()

# Register new user
def register_user():
    def capture_images():
        Id = int(entry_id.get())
        Name = entry_name.get()
        age = int(entry_age.get())

        insertupdater(Id, Name, age)

        facedetect = cv2.CascadeClassifier('haarcascade_frontalface_default.xml')
        cam = cv2.VideoCapture(0)

        samplenum = 0
        while True:
            ret, img = cam.read()
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            faces = facedetect.detectMultiScale(gray, 1.3, 5)
            for (x, y, w, h) in faces:
                samplenum += 1
                cv2.imwrite(f"dataset/user.{Id}.{samplenum}.jpg", gray[y:y+h, x:x+w])
                cv2.rectangle(img, (x, y), (x+w, y+h), (0, 0, 255), 2)  # Red color rectangle
                cv2.waitKey(100)
            cv2.imshow("Face", img)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
            if samplenum > 20:
                break

        cam.release()
        cv2.destroyAllWindows()
        messagebox.showinfo("Info", "User registered and face images captured.")

        # Train recognizer
        train_recognizer()

    # New window for registration
    register_window = tk.Toplevel(root)
    register_window.title("Register New student")

    tk.Label(register_window, text="Enter Student Roll No:", font=("Arial", 14)).grid(row=0, column=0, padx=10, pady=10)
    entry_id = tk.Entry(register_window, font=("Arial", 14))
    entry_id.grid(row=0, column=1, padx=10, pady=10)

    tk.Label(register_window, text="Enter Student Name:", font=("Arial", 14)).grid(row=1, column=0, padx=10, pady=10)
    entry_name = tk.Entry(register_window, font=("Arial", 14))
    entry_name.grid(row=1, column=1, padx=10, pady=10)

    tk.Label(register_window, text="Enter Student Age:", font=("Arial", 14)).grid(row=2, column=0, padx=10, pady=10)
    entry_age = tk.Entry(register_window, font=("Arial", 14))
    entry_age.grid(row=2, column=1, padx=10, pady=10)

    tk.Button(register_window, text="Capture Images", font=("Arial", 14), command=capture_images).grid(row=3, column=0, columnspan=2, pady=20)

# Train recognizer
def train_recognizer():
    recognizer = cv2.face.LBPHFaceRecognizer_create()
    path = "dataset"

    def get_img_id(path):
        img_path = [os.path.join(path, f) for f in os.listdir(path)]
        faces = []
        ids = []
        for single_img_path in img_path:
            faceimg = Image.open(single_img_path).convert('L')
            faceNP = np.array(faceimg, np.uint8)
            id = int(os.path.split(single_img_path)[-1].split(".")[1])
            faces.append(faceNP)
            ids.append(id)
            cv2.imshow("Training", faceNP)
            cv2.waitKey(10)
        return np.array(ids), faces

    ids, faces = get_img_id(path)
    recognizer.train(faces, ids)
    recognizer.save("recognizers/trainingdata.yml")
    cv2.destroyAllWindows()

# Mark attendance
def mark_attendance():
    def update_status(status, name="", roll_no=""):
        status_label.config(text=status)
        name_label.config(text=f"Name: {name}")
        roll_label.config(text=f"Roll No: {roll_no}")

    def getprofile(id):
        cursor = myd.cursor()
        cursor.execute("SELECT * FROM STUDENT WHERE ID=%s", (id,))
        profile = cursor.fetchone()
        cursor.close()
        return profile

    def is_already_marked(id):
        cursor = myd.cursor()
        now = datetime.now()
        date_today = now.strftime("%Y-%m-%d")
        cursor.execute("SELECT * FROM attendance WHERE id=%s AND DATE(time)=%s", (id, date_today))
        record = cursor.fetchone()
        cursor.close()
        return record is not None

    myd = pymysql.connect(host="localhost", user="root", passwd="aditya2808", database="college")
    mycursor = myd.cursor()
    speak = pr.init()
    facedetect = cv2.CascadeClassifier("haarcascade_frontalface_default.xml")
    cam = cv2.VideoCapture(0)
    recognizer = cv2.face.LBPHFaceRecognizer_create()
    recognizer.read("recognizers/trainingdata.yml")

    confidence_threshold = 70
    last_detection_time = time.time()

    def update_frame():
        nonlocal last_detection_time
        ret, frame = cam.read()
        if not ret:
            return
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = facedetect.detectMultiScale(gray, 1.3, 5)
        for (x, y, w, h) in faces:
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
            id, conf = recognizer.predict(gray[y:y+h, x:x+w])
            profile = getprofile(id)
            if conf <= confidence_threshold:
                if profile is not None:
                    a = profile[1]
                    b = profile[2]
                    c = profile[0]
                    now = datetime.now()
                    d = now.strftime("%Y-%m-%d %H:%M:%S")

                    if is_already_marked(c):
                        update_status("Attendance already marked", a, c)
                        speak.say("Attendance is already marked")
                        speak.runAndWait()
                        time.sleep(3)
                    else:
                        if time.time() - last_detection_time > 5:
                            update_status("Attendance marked", a, c)
                            speak.say(f"{a} is present")
                            speak.runAndWait()
                            sql_insert_query = "INSERT INTO attendance (id, name, age, time) VALUES (%s, %s, %s, %s)"
                            mycursor.execute(sql_insert_query, (c, a, b, d))
                            myd.commit()
                            last_detection_time = time.time()
                else:
                    update_status("face not detected")
                    cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 0, 255), 2)
                    cv2.putText(frame, "face not detected", (x, y + h + 20), cv2.FONT_HERSHEY_COMPLEX, 1, (0, 0, 255), 2)
            else:
                update_status("face not detected")

        # Convert frame to PIL Image and update UI
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(frame_rgb)
        img_tk = ImageTk.PhotoImage(image=img)
        face_canvas.create_image(0, 0, anchor=tk.NW, image=img_tk)
        face_canvas.img_tk = img_tk

        face_window.after(10, update_frame)  # Call this function again after 10ms

    # Create the face detection window
    face_window = tk.Toplevel(root)
    face_window.title("Face Detection")
    face_window.geometry("640x480")
    face_window.configure(bg="#2c3e50")

    face_canvas = tk.Canvas(face_window, width=640, height=400)
    face_canvas.pack(pady=10)

    status_frame = tk.Frame(face_window, bg="#2c3e50")
    status_frame.pack()

    status_label = tk.Label(status_frame, text="", font=("Arial", 14), bg="#2c3e50", fg="white")
    status_label.pack(pady=5)

    name_label = tk.Label(status_frame, text="", font=("Arial", 14), bg="#2c3e50", fg="white")
    name_label.pack(pady=5)

    roll_label = tk.Label(status_frame, text="", font=("Arial", 14), bg="#2c3e50", fg="white")
    roll_label.pack(pady=5)

    update_frame()

# Main window
root = tk.Tk()
root.title("Face Detection and Attendance System")
root.geometry("400x300")
root.configure(bg="#2c3e50")

title_frame = tk.Frame(root, bg="#2c3e50")
title_frame.pack(pady=20)

tk.Label(title_frame, text="Face Detection System", font=("Arial", 24), bg="#2c3e50", fg="white").pack()

button_frame = tk.Frame(root, bg="#2c3e50")
button_frame.pack(pady=20)

tk.Button(button_frame, text="Register User", font=("Arial", 14), command=register_user, bg="#1abc9c", fg="white", width=20).grid(row=0, column=0, padx=10, pady=10)
tk.Button(button_frame, text="Mark Attendance", font=("Arial", 14), command=mark_attendance, bg="#e74c3c", fg="white", width=20).grid(row=1, column=0, padx=10, pady=10)

root.mainloop()


