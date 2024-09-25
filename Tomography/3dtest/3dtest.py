import cv2
import numpy as np
import matplotlib.pyplot as plt
import open3d as o3d
import os

def load_images_from_folder(folder):
    images = []
    for filename in sorted(os.listdir(folder)):
        img = cv2.imread(os.path.join(folder, filename))
        if img is not None:
            images.append(img)
    return images

def find_keypoints_and_descriptors(images):
    orb = cv2.ORB_create()
    keypoints = []
    descriptors = []

    for img in images:
        kp, des = orb.detectAndCompute(img, None)
        keypoints.append(kp)
        descriptors.append(des)

    return keypoints, descriptors

def match_keypoints(descriptors):
    bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
    matches = []

    for i in range(len(descriptors) - 1):
        matches.append(bf.match(descriptors[i], descriptors[i + 1]))

    return matches

def draw_matches(images, keypoints, matches):
    for i in range(len(matches)):
        img_matches = cv2.drawMatches(images[i], keypoints[i], images[i + 1], keypoints[i + 1], matches[i], None, flags=cv2.DrawMatchesFlags_NOT_DRAW_SINGLE_POINTS)
        plt.imshow(img_matches)
        plt.title(f'Matches between Image {i} and Image {i + 1}')
        plt.show()

def reconstruct_3d(images, keypoints, matches):
    points_3d = []
    camera_matrices = []

    # Initialize camera matrix (assume a simple intrinsic matrix)
    focal_length = 800
    cx = images[0].shape[1] / 2
    cy = images[0].shape[0] / 2
    K = np.array([[focal_length, 0, cx],
                  [0, focal_length, cy],
                  [0, 0, 1]])

    for i in range(len(matches)):
        src_pts = np.float32([keypoints[i][m.queryIdx].pt for m in matches[i]]).reshape(-1, 2)
        dst_pts = np.float32([keypoints[i + 1][m.trainIdx].pt for m in matches[i]]).reshape(-1, 2)

        E, mask = cv2.findEssentialMat(src_pts, dst_pts, K, method=cv2.RANSAC, prob=0.999, threshold=1.0)
        _, R, t, mask = cv2.recoverPose(E, src_pts, dst_pts, K)

        # Add camera pose to the list
        if i == 0:
            # First camera at the origin
            camera_matrices.append(np.hstack((np.eye(3), np.zeros((3, 1)))))
        else:
            # Subsequent cameras
            camera_matrices.append(np.hstack((R, t)))

        # Triangulate points
        P1 = K @ camera_matrices[i - 1]  # Previous camera matrix
        P2 = K @ camera_matrices[i]      # Current camera matrix
        points_4d = cv2.triangulatePoints(P1, P2, src_pts.T, dst_pts.T)
        points_3d.append(points_4d[:3] / points_4d[3])  # Normalize

    return np.hstack(points_3d)

def visualize_mesh(points_3d):
    # Create point cloud from 3D points
    pcd = o3d.geometry.PointCloud()
    pcd.points = o3d.utility.Vector3dVector(points_3d.T)

    # Estimate normals
    pcd.estimate_normals(search_param=o3d.geometry.KDTreeSearchParamHybrid(radius=0.1, max_nn=30))

    # Perform Poisson surface reconstruction
    mesh, densities = o3d.geometry.TriangleMesh.create_from_point_cloud_poisson(pcd, depth=9)

    # Crop the mesh based on density
    vertices_to_remove = densities < np.quantile(densities, 0.5)
    mesh.remove_vertices_by_index(np.where(vertices_to_remove)[0])

    # Visualize the mesh
    o3d.visualization.draw_geometries([mesh], window_name="3D Mesh Reconstruction")

if __name__ == "__main__":
    folder_path = 'C:/Users/jared/OneDrive/Desktop/GPOE2025/Tomography_Main/Tomography/3dtest/images'
    images = load_images_from_folder(folder_path)

    if not images:
        print("No images found in the specified folder.")
        exit(1)

    keypoints, descriptors = find_keypoints_and_descriptors(images)
    matches = match_keypoints(descriptors)
    draw_matches(images, keypoints, matches)

    points_3d = reconstruct_3d(images, keypoints, matches)

    visualize_mesh(points_3d)

    print(f"Reconstructed {points_3d.shape[1]} 3D points.")
