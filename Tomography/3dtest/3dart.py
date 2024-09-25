import os
import cv2
import numpy as np
from mpl_toolkits.mplot3d import Axes3D
import matplotlib.pyplot as plt
from skimage import measure

# Parameters
alpha = 0.1  # Step size for ART
num_iterations = 50  # Number of iterations
voxel_size = 7  # Size of the voxel grid

# Camera intrinsics (example values, adjust as needed)
focal_length = 1.0
camera_matrix = np.array([[focal_length, 0, voxel_size / 2],
                           [0, focal_length, voxel_size / 2],
                           [0, 0, 1]])

# Example camera extrinsics: [translation_x, translation_y, translation_z, rotation_angle]
camera_positions = [
    [0, 0, 0, 0],  # Camera 1
    [5, 0, 5, np.pi / 4],  # Camera 2 (45 degrees rotation)
    [-1, 0, 5, -np.pi / 4],  # Camera 3 (-45 degrees rotation)
]

# Load images from a folder and associate them with camera indices
def load_images_from_folder(folder, camera_count):
    camera_images = {i: [] for i in range(camera_count)}  # Dictionary to hold images per camera
    for i in range(camera_count):
        camera_folder = os.path.join(folder, f'camera_{i}')
        if os.path.exists(camera_folder):
            for filename in os.listdir(camera_folder):
                if filename.endswith(('.jpg', '.jpeg', '.png')):  # Add other formats if needed
                    img_path = os.path.join(camera_folder, filename)
                    img = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
                    if img is not None:
                        camera_images[i].append(img)
    return camera_images

# Initialize 3D volume (voxel grid)
def initialize_volume(size):
    return np.zeros((size, size, size), dtype=np.float32)

# Function to create a rotation matrix
def rotation_matrix(angle):
    c = np.cos(angle)
    s = np.sin(angle)
    return np.array([[c, -s, 0],
                     [s, c, 0],
                     [0, 0, 1]])

# Projection function
def project(volume, position, rotation_angle):
    # Create a rotation matrix based on the rotation angle
    rotation = rotation_matrix(rotation_angle)

    # Create a combined transformation matrix
    transformation_matrix = np.eye(4)
    transformation_matrix[:3, :3] = rotation
    transformation_matrix[:3, 3] = position

    # Prepare the volume for projection
    volume_shape = volume.shape
    projected_image = np.zeros((voxel_size, voxel_size), dtype=np.float32)

    # Iterate over each voxel and apply the projection
    for x in range(volume_shape[0]):
        for y in range(volume_shape[1]):
            for z in range(volume_shape[2]):
                # Point in 3D space
                point_3d = np.array([x, y, z, 1])  # Homogeneous coordinates

                # Apply the transformation matrix
                transformed_point = transformation_matrix @ point_3d

                # Project to 2D
                x_proj = int(transformed_point[0] / transformed_point[2])
                y_proj = int(transformed_point[1] / transformed_point[2])

                # Check bounds and accumulate intensity
                if 0 <= x_proj < voxel_size and 0 <= y_proj < voxel_size:
                    projected_image[y_proj, x_proj] += volume[x, y, z]

    return projected_image

# Update function based on ART
def update_volume(volume, observed, projected):
    # Calculate residuals
    residual = observed.astype(np.float32) - projected.astype(np.float32)
    
    # Clamp residuals to avoid extreme updates
    residual = np.clip(residual, -255, 255)

    # Update volume
    volume += alpha * residual[:, :, np.newaxis]

    # Prevent volume from exceeding reasonable limits
    volume = np.clip(volume, 0, 255)

    return volume

# Main reconstruction function
def reconstruct(camera_images):
    volume = initialize_volume(voxel_size)

    for i in range(num_iterations):
        for cam_index, images in camera_images.items():
            for img in images:
                # Resize the image to match the voxel grid size
                resized_img = cv2.resize(img, (voxel_size, voxel_size))

                # Project the current volume using the camera position and rotation
                projected = project(volume, camera_positions[cam_index][:3], camera_positions[cam_index][3])

                # Update the volume with the resized image and projected volume
                volume = update_volume(volume, resized_img, projected)

    return volume

# Visualize 3D volume using isosurface extraction
def visualize_volume(volume):
    # Extract the isosurface
    verts, faces, _, _ = measure.marching_cubes(volume, level=0.25)

    # Plotting the surface
    fig = plt.figure()
    ax = fig.add_subplot(111, projection='3d')
    ax.plot_trisurf(verts[:, 0], verts[:, 1], verts[:, 2], triangles=faces, color='cyan', linewidth=0.1, antialiased=True)
    ax.set_title('Reconstructed 3D Object')
    plt.show()

# Main execution
if __name__ == "__main__":
    folder_path = 'C:/Users/jared/OneDrive/Desktop/GPOE2025/Tomography_Main/Tomography/3dtest/images'  # Replace with your folder path
    camera_count = len(camera_positions)  # Number of cameras
    camera_images = load_images_from_folder(folder_path, camera_count)
    if camera_images:
        volume = reconstruct(camera_images)
        visualize_volume(volume)
    else:
        print("No images found in the specified folder.")