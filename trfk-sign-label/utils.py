import numpy as np
from PIL import Image, ImageDraw, ImageColor, ImageFont


def draw_bounding_box_on_image(image, ymin, xmin, ymax, xmax,
                               color, font, thickness=1, display_str_list=()):
    """
    Adds a bounding box to an image.

    Args:
        image -- the image object
        ymin -- bounding box coordinate
        xmin -- bounding box coordinate
        ymax -- bounding box coordinate
        xmax -- bounding box coordinate
        color -- color for the bounding box edges
        font -- font for class label
        thickness -- edge thickness of the bounding box
        display_str_list -- class labels for each object detected


    Returns:
        No return.  The function modifies the `image` argument 
                    that gets passed into this function

    """
    draw = ImageDraw.Draw(image)

    # scale the bounding box coordinates to the height and width of the image
    (left, right, top, bottom) = (xmin, xmax, ymin, ymax)

    # define the four edges of the detection box
    draw.line([(left, top), (left, bottom), (right, bottom), (right, top), (left, top)],
              width=thickness, fill=color)

    # If the total height of the display strings added to the top of the bounding
    # box exceeds the top of the image, stack the strings below the bounding box
    # instead of above.
    display_str_heights = [font.getsize(ds)[1] for ds in display_str_list]

    # Each display_str has a top and bottom margin of 0.05x.
    total_display_str_height = (1 + 2 * 0.05) * sum(display_str_heights)

    if top > total_display_str_height:
        text_bottom = top
    else:
        text_bottom = top + total_display_str_height

    # Reverse list and print from bottom to top.
    for display_str in display_str_list[::-1]:
        text_width, text_height = font.getsize(display_str)
        margin = np.ceil(0.05 * text_height)
        draw.rectangle([(left, text_bottom - text_height - 2 * margin),
                        (left + text_width, text_bottom)], fill=color)
        draw.text((left + margin, text_bottom - text_height - margin),
                  display_str, fill="black", font=font)
        text_bottom -= text_height - 2 * margin


def draw_boxes(image, boxes, class_names, prediction, scores=None, max_boxes=10, min_score=0.1):
    """
    Overlay labeled boxes on an image with formatted scores and label names.

    Args:
        image -- the image as a numpy array
        boxes -- list of detection boxes
        class_names -- list of classes for each detected object
        scores -- numbers showing the model's confidence in detecting that object
        max_boxes -- maximum detection boxes to overlay on the image (default is 10)
        min_score -- minimum score required to display a bounding box

    Returns:
        image -- the image after detection boxes and classes are overlaid on the original image.
    """

    colors = list(ImageColor.colormap.values())

    font = ImageFont.load_default()

    if not prediction:
        scores = 1

    # only display detection boxes that have the minimum score or higher
    for index, score in enumerate(scores):
        if score >= min_score:
            xmin, ymin, xmax, ymax = tuple(boxes[index])

            if xmin + xmax + ymin + ymax == 0:
                return image

            display_str = "{}: {}%".format(class_names[index], int(100 * score))

            color = 'blue'
            image_pil = Image.fromarray(np.uint8(image)).convert("RGB")

            # draw one bounding box and overlay the class labels onto the image
            draw_bounding_box_on_image(image_pil,ymin,xmin,ymax,xmax,color,font,
                                       display_str_list=[display_str])

            np.copyto(image, np.array(image_pil))

    return image
