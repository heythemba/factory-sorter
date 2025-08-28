#!/usr/bin/env python3
import argparse
import cv2
import numpy as np

def detect_shape(contour):
    """Return a shape name given a contour."""
    peri = cv2.arcLength(contour, True)
    approx = cv2.approxPolyDP(contour, 0.04 * peri, True)

    # Triangle
    if len(approx) == 3:
        return "Triangle"

    # Quadrilateral: square vs rectangle using aspect ratio
    if len(approx) == 4:
        (x, y, w, h) = cv2.boundingRect(approx)
        ar = w / float(h) if h != 0 else 0
        return "Carre" if 0.95 <= ar <= 1.05 else "Rectangle"

    # Circle / ellipse (fallback for polygons with many vertices)
    if len(approx) > 4:
        area = cv2.contourArea(contour)
        if area <= 0:
            return "Inconnu"
        perimeter = cv2.arcLength(contour, True)
        if perimeter == 0:
            return "Inconnu"
        circularity = 4 * np.pi * (area / (perimeter * perimeter))
        return "Cercle" if circularity > 0.75 else "Ellipse/Polygone"

    return "Inconnu"


def main():
    parser = argparse.ArgumentParser(description="Detect contours, identify shape, and compute area.")
    parser.add_argument("--source", type=str, default="0",
                        help="Video source: camera index (e.g., '0') or path to a video/image file.")
    parser.add_argument("--min-area", type=float, default=500.0,
                        help="Minimum contour area in pixels to keep (default: 500).")
    parser.add_argument("--show-edges", action="store_true",
                        help="Also display the Canny edges window.")
    args = parser.parse_args()

    # Decide input source (webcam index vs file path)
    source = 0
    if args.source.isdigit():
        source = int(args.source)
    else:
        source = args.source

    cap = cv2.VideoCapture(source)

    if not cap.isOpened():
        raise SystemExit(f"Could not open source: {args.source}")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # Preprocess
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        edges = cv2.Canny(blurred, 50, 150)

        # Find contours
        contours, _ = cv2.findContours(edges.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        out = frame.copy()
        for c in contours:
            area = cv2.contourArea(c)
            if area < args.min_area:
                continue

            # Identify shape
            shape = detect_shape(c)

            # Moments for centroid
            M = cv2.moments(c)
            if M["m00"] != 0:
                cX = int(M["m10"] / M["m00"])
                cY = int(M["m01"] / M["m00"])
            else:
                cX, cY = 0, 0

            # Draw contour and annotations
            cv2.drawContours(out, [c], -1, (0, 255, 0), 2)
            cv2.putText(out, f"{shape} | Area: {int(area)} px^2",
                        (max(cX - 80, 10), max(cY - 10, 20)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

        cv2.imshow("Shapes & Areas", out)
        if args.show_edges:
            cv2.imshow("Edges (Canny)", edges)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
