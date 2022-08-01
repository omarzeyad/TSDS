import cv2
import numpy as np
import pandas as pd
import tflite_runtime.interpreter as tflite
import time
import os, random
from utils import draw_boxes


class Localization_Model:
    def __init__(self, weights, class_names, image_size=640, conf_thres=0.25, iou_thres=0.45):
        self.weights = weights
        self.image_size = image_size
        self.conf_thres = conf_thres
        self.iou_thres = iou_thres
        self.interpreter = tflite.Interpreter(self.weights)
        self.interpreter.allocate_tensors()
        self.input_details = self.interpreter.get_input_details()
        self.output_details = self.interpreter.get_output_details()
        with open(class_names) as f:
            self.class_names = [line.rstrip() for line in f]

    def xywh2xyxy(self, x):
        # Convert nx4 boxes from [x, y, w, h] to [x1, y1, x2, y2] where xy1=top-left, xy2=bottom-right
        y = x.copy()
        y[:, 0] = x[:, 0] - x[:, 2] / 2  # top left x
        y[:, 1] = x[:, 1] - x[:, 3] / 2  # top left y
        y[:, 2] = x[:, 0] + x[:, 2] / 2  # bottom right x
        y[:, 3] = x[:, 1] + x[:, 3] / 2  # bottom right y
        return y

    def non_max_suppression(self, boxes, scores, threshold):
        assert boxes.shape[0] == scores.shape[0]
        # bottom-left origin
        ys1 = boxes[:, 0]
        xs1 = boxes[:, 1]
        # top-right target
        ys2 = boxes[:, 2]
        xs2 = boxes[:, 3]
        # box coordinate ranges are inclusive-inclusive
        areas = (ys2 - ys1) * (xs2 - xs1)
        scores_indexes = scores.argsort().tolist()
        boxes_keep_index = []
        while len(scores_indexes):
            index = scores_indexes.pop()
            boxes_keep_index.append(index)
            if not len(scores_indexes):
                break
            ious = self.compute_iou(boxes[index], boxes[scores_indexes], areas[index], areas[scores_indexes])
            filtered_indexes = set((ious > threshold).nonzero()[0])
            # if there are no more scores_index
            # then we should pop it
            scores_indexes = [
                v for (i, v) in enumerate(scores_indexes)
                if i not in filtered_indexes
            ]
        return np.array(boxes_keep_index)

    def compute_iou(self, box, boxes, box_area, boxes_area):
        # this is the iou of the box against all other boxes
        assert boxes.shape[0] == boxes_area.shape[0]
        # get all the origin-ys
        # push up all the lower origin-xs, while keeping the higher origin-xs
        ys1 = np.maximum(box[0], boxes[:, 0])
        # get all the origin-xs
        # push right all the lower origin-xs, while keeping higher origin-xs
        xs1 = np.maximum(box[1], boxes[:, 1])
        # get all the target-ys
        # pull down all the higher target-ys, while keeping lower origin-ys
        ys2 = np.minimum(box[2], boxes[:, 2])
        # get all the target-xs
        # pull left all the higher target-xs, while keeping lower target-xs
        xs2 = np.minimum(box[3], boxes[:, 3])
        # each intersection area is calculated by the
        # pulled target-x minus the pushed origin-x
        # multiplying
        # pulled target-y minus the pushed origin-y
        # we ignore areas where the intersection side would be negative
        # this is done by using maxing the side length by 0
        intersections = np.maximum(ys2 - ys1, 0) * np.maximum(xs2 - xs1, 0)
        # each union is then the box area
        # added to each other box area minusing their intersection calculated above
        unions = box_area + boxes_area - intersections
        # element wise division
        # if the intersection is 0, then their ratio is 0
        ious = intersections / unions
        return ious

    def nms(self, prediction):
        prediction = prediction[prediction[..., 4] > self.conf_thres]

        # Box (center x, center y, width, height) to (x1, y1, x2, y2)
        boxes = self.xywh2xyxy(prediction[:, :4])

        res = self.non_max_suppression(boxes, prediction[:, 4], self.iou_thres)

        result_boxes = []
        result_scores = []
        result_class_names = []
        for r in res:
            # if self.class_names[np.argmax(prediction[r, 5:])] == 'Traffic Sign':
            result_boxes.append(boxes[r])
            result_scores.append(prediction[r, 4])
            result_class_names.append(self.class_names[np.argmax(prediction[r, 5:])])

        return result_boxes, result_scores, result_class_names

    def localize(self, image):
        original_size = image.shape[:2]
        input_data = np.ndarray(shape=(1, self.image_size, self.image_size, 3), dtype=np.float32)
        image = cv2.resize(image, (self.image_size, self.image_size))
        input_data[0] = image.astype(np.float32)/255.0

        self.interpreter.set_tensor(self.input_details[0]['index'], input_data)
        self.interpreter.invoke()
        pred = self.interpreter.get_tensor(self.output_details[0]['index'])

        # Denormalize xywh
        pred[..., 0] *= original_size[1]  # x
        pred[..., 1] *= original_size[0]  # y
        pred[..., 2] *= original_size[1]  # w
        pred[..., 3] *= original_size[0]  # h

        result_boxes, result_scores, result_class_names = self.nms(pred)

        return result_boxes, result_scores, result_class_names


class Classification_Model:
    def __init__(self, weights, class_names, image_size=100, conf_thres=0.25):
        self.weights = weights
        self.image_size = image_size
        self.conf_thres = conf_thres
        self.interpreter = tflite.Interpreter(self.weights)
        self.interpreter.allocate_tensors()
        self.input_details = self.interpreter.get_input_details()
        self.output_details = self.interpreter.get_output_details()
        self.class_names = pd.read_csv(class_names)

    def predict(self, image):
        image = cv2.resize(image, (100, 100))
        input_data = np.ndarray(shape=(1, 100, 100, 3), dtype=np.float32)
        input_data[0] = image.astype(np.float32)/255.0

        self.interpreter.set_tensor(self.input_details[0]['index'], input_data)
        self.interpreter.invoke()
        pred = self.interpreter.get_tensor(self.output_details[0]['index'])
        pred = pred.argmax()

        pred = self.class_names[self.class_names.ClassId == pred].ClassName[pred]
        return pred

    def classify(self, RGB_img, result_boxes, result_objects):
        results = []
        for i, name in enumerate(result_objects):
            if name == 'Traffic Sign':
                xmin, ymin, xmax, ymax = result_boxes[i]
                xmin = int(xmin)
                ymin = int(ymin)
                xmax = int(xmax)
                ymax = int(ymax)

                image = RGB_img[ymin:ymax, xmin:xmax, :]

                pred = self.predict(image)
                results.append(pred)
            else:
                results.append(name)

        return results


if __name__ == "__main__":
    # Load models
    localizer = Localization_Model(weights='models/localizer.tflite', class_names='models/classes.txt')
    classifier = Classification_Model(weights='models/classifier.tflite', class_names='models/labels.csv')

    # Pick and load an image
    picked_img = random.choice(os.listdir('images/'))
    print(f'picked image: {picked_img}\n')
    
    img = cv2.imread(f'images/{picked_img}', cv2.IMREAD_COLOR)
    RGB_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

    # Pipeline models
    start = time.perf_counter()
    bounding_boxes, scores, localized_objects = localizer.localize(RGB_img)
    end = time.perf_counter()
    print(f'localizer took: {end-start:0.2f}')
    print(scores, localized_objects)

    start = time.perf_counter()
    labels = classifier.classify(RGB_img, bounding_boxes, localized_objects)
    end = time.perf_counter()
    print(f'classifier took: {end-start:0.2f}')
    print(labels)

    # Draw bounding boxes on the image and save it
    image = draw_boxes(RGB_img, bounding_boxes, labels, prediction=True, scores=scores)

    BGR_img = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
    cv2.imwrite(f'results/{picked_img}', BGR_img)