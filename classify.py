# import the necessary packages
from tensorflow.keras.preprocessing.image import img_to_array
from tensorflow.keras.models import load_model
import numpy as np
import argparse
import imutils
import pickle
import cv2
import os

# construct the argument parser and parse the arguments
ap = argparse.ArgumentParser()
ap.add_argument("-m", "--model", required=True,
	help="path to trained model model")
args = vars(ap.parse_args())

DATADIR = "Project_Images/"
CATEGORIES = ["ng", "ok","shuffle"]
IMG_SIZE = 100

print("[INFO] loading network...")
model = load_model(args["model"])

for category in CATEGORIES:
	path = os.path.join(DATADIR, category)
	class_num = CATEGORIES.index(category)
	for img in os.listdir(path):
		try:
			print("Real",category)
			image = cv2.imread(os.path.join(path,img), cv2.IMREAD_GRAYSCALE)
			image = cv2.resize(image, (IMG_SIZE, IMG_SIZE))
			image = np.array(image).reshape(-1, IMG_SIZE, IMG_SIZE, 1)
			image = image / 255
			print("[INFO] classifying image...")
			proba = model.predict(image)[0]
			label = np.where(proba > .5, 1,0)
			correct = "Good" if label == 1 else "Not Good"
			print("[INFO] {}".format(correct))
			print(img,"\n")
		except Exception as e:
			pass