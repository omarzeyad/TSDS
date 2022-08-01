import os, random
import threading
import pybleno
from models import *
from thread_job import ThreadJob
import cv2
import time
import re


class LabelCharacteristic(pybleno.Characteristic):
    def __init__(self, uuid):
        pybleno.Characteristic.__init__(self, {
            'uuid': uuid,
            'properties': ['notify'],
            'value': None
        })

        # Load models
        self.localizer = Localization_Model(weights='models/localizer.tflite', class_names='models/classes.txt')
        self.classifier = Classification_Model(weights='models/classifier.tflite', class_names='models/labels.csv')

        self.lbl_thread = ThreadJob(self.onSignDetect, threading.Event(), 0)
        self.lbl_thread.start()

        self._value = 'No_LABEL'
        self._updateValueCallback = None

    def onSubscribe(self, maxValueSize, updateValueCallback):
        print('LabelCharacteristic -> onSubscribe')
        self._updateValueCallback = updateValueCallback
        self.lbl_thread.resume()

    def onUnsubscribe(self):
        print('LabelCharacteristic -> onUnsubscribe')
        self._updateValueCallback = None
        self.lbl_thread.pause()

    def onSignDetect(self):
        # Pick and load an image
        picked_img = random.choice(os.listdir('images/'))
        print(f'picked image: {picked_img}')
        
        camera_shot = cv2.imread(f'images/{picked_img}', cv2.IMREAD_COLOR)
        RGB_img = cv2.cvtColor(camera_shot, cv2.COLOR_BGR2RGB)

        # Pipeline models
        start = time.time()
        bounding_boxes, scores, localized_objects = self.localizer.localize(RGB_img)
        labels = self.classifier.classify(RGB_img, bounding_boxes, localized_objects)
        end = time.time()
        print(f'Took: {end - start:0.4f}')
        
        self._value = re.sub(r"[\[\]']", "", str(labels))

        # Notify driver and save result_image if at least one sign is found
        if self._updateValueCallback and self._value != '':
            print(f'LabelCharacteristic -> onLabelUpdate: notifying [{self._value}]')
            self._updateValueCallback(self._value.encode())
        
            # Draw bounding boxes on the image and save it
            result_image = draw_boxes(RGB_img, bounding_boxes, labels, prediction=True, scores=scores)
            BGR_img = cv2.cvtColor(result_image, cv2.COLOR_RGB2BGR)
            cv2.imwrite(f'results/{picked_img}', BGR_img)