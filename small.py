import cv2
import numpy as np
import matplotlib.pyplot as plt
import os
from roboflow import Roboflow
import base64
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Load model
rf = Roboflow(api_key="MNbIhwpAq2AETXba1jPA")
project = rf.workspace().project("car-plate-mav1h-rhegv")
model = project.version(1).model

def process_vehicle_plate(vehicle_img_path, plate_img_path, model):
    """
    Replaces a vehicle's license plate.

    Args:
        vehicle_img_path: Path to vehicle image
        plate_img_path: Path to new license plate image
        model: segmentation model
    """
    try:
        # 1. Load images
        vehicle_img = cv2.cvtColor(cv2.imread(vehicle_img_path), cv2.COLOR_BGR2RGB)
        new_lp = cv2.cvtColor(cv2.imread(plate_img_path), cv2.COLOR_BGR2RGB)

        # 2. run inference
        result = model.predict(vehicle_img_path, confidence=40).json()

        polygon_points = []
        for pred in result['predictions']:
            if pred['class'] == 'plate':
                polygon_points.extend([[p['x'], p['y']] for p in pred['points']])

        if len(polygon_points) < 4:
            raise ValueError("Plate detection failed: <4 points found")

        polygon_points = np.array(polygon_points, dtype=np.float32)
        contour = polygon_points.reshape((-1, 1, 2))
        epsilon = 0.02 * cv2.arcLength(contour, closed=True)
        approx_corners = cv2.approxPolyDP(contour, epsilon, closed=True)

        if len(approx_corners) == 4:
            corners = approx_corners.reshape(4, 2)
        else:
            rect = cv2.minAreaRect(contour)
            corners = cv2.boxPoints(rect).astype(np.int32)

        center = np.mean(corners, axis=0)

        def sort_corners(pts, center):
            def angle_from_center(pt):
                return np.arctan2(pt[1] - center[1], pt[0] - center[0])
            return sorted(pts, key=angle_from_center)

        sorted_pts = sort_corners(corners, center)
        sorted_pts = np.array(sorted_pts, dtype=np.float32)

        top_two = sorted(sorted_pts[:2], key=lambda p: p[0])  # left to right
        bottom_two = sorted(sorted_pts[2:], key=lambda p: p[0])  # left to right

        dst_pts = np.array([
            top_two[0],
            top_two[1],
            bottom_two[1],
            bottom_two[0]
        ], dtype=np.float32)

        h, w = new_lp.shape[:2]
        src_pts = np.float32([
            [0, 0],
            [w, 0],
            [w, h],
            [0, h]
        ])

        M = cv2.getPerspectiveTransform(src_pts, dst_pts)
        warped_lp = cv2.warpPerspective(new_lp, M, (vehicle_img.shape[1], vehicle_img.shape[0]))

        gray = cv2.cvtColor(warped_lp, cv2.COLOR_BGR2GRAY)
        _, mask = cv2.threshold(gray, 1, 255, cv2.THRESH_BINARY)
        mask_inv = cv2.bitwise_not(mask)

        lp_mask = np.zeros((vehicle_img.shape[0], vehicle_img.shape[1]), dtype=np.uint8)
        polygon_contour = np.array(polygon_points, dtype=np.int32).reshape((-1, 1, 2))
        cv2.fillPoly(lp_mask, [polygon_contour], color=255)
        lp_mask = cv2.GaussianBlur(lp_mask, (5, 5), 0)
        _, lp_mask = cv2.threshold(lp_mask, 127, 255, cv2.THRESH_BINARY)

        # Plate removal
        inpainted = cv2.inpaint(vehicle_img, lp_mask, inpaintRadius=3, flags=cv2.INPAINT_TELEA)
        bg = cv2.bitwise_and(inpainted, inpainted, mask=mask_inv)
        fg = cv2.bitwise_and(warped_lp, warped_lp, mask=mask)
        naive_pasted = cv2.add(bg, fg)

        # Convert the result to base64 for sending back to the frontend
        _, buffer = cv2.imencode('.jpg', cv2.cvtColor(naive_pasted, cv2.COLOR_RGB2BGR))
        result_base64 = base64.b64encode(buffer).decode('utf-8')
        return result_base64

    except Exception as e:
        print(f"Error processing image: {str(e)}")
        return None

@app.route('/')
def index():
    return render_template('signin.html')

@app.route('/process-image', methods=['POST'])
def process_image():
    try:
        # Get the base64 image data from the request
        data = request.json
        image_data = data['image'].split(',')[1]  # Remove the data URL prefix
        plate_img_path = "C:\\Users\\DELL\\Documents\\Automation\\tailadmin-free-tailwind-dashboard-template-main\\plate.jpg"
        
        # Save the uploaded image temporarily
        temp_img_path = "temp_upload.jpg"
        with open(temp_img_path, 'wb') as f:
            f.write(base64.b64decode(image_data))
        
        # Process the image
        result = process_vehicle_plate(temp_img_path, plate_img_path, model)
        
        # Clean up the temporary file
        os.remove(temp_img_path)
        
        if result:
            return jsonify({'success': True, 'result': result})
        else:
            return jsonify({'success': False, 'error': 'Processing failed'})
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

if __name__ == '__main__':
    app.run(port=5003)