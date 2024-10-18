import os
import cv2
import numpy as np
from mpl_toolkits.mplot3d import Axes3D
import matplotlib.pyplot as plt
from skimage import measure

# Parameters
alpha = 0.1  # Step size for ART
num_iterations = 1  # Number of iterations
voxel_size = 2  # Physical size of the voxels
num_voxels = 10  # Number of voxels in each dimension

# Camera intrinsics (example values, adjust as needed)
focal_length = 1.0
camera_matrix = np.array([[focal_length, 0, voxel_size / 2],
                           [0, focal_length, voxel_size / 2],
                           [0, 0, 1]])

# Example camera extrinsics: [translation_x, translation_y, translation_z, az_rotation_angle, polar_angle]
camera_positions = [
    [-25, 15, 20, -3.6*np.pi/8, 0],  # Camera 1
    [25, 15, 20, 1.4*3*np.pi/4, 0],  # Camera 2 
    [0, -25, 20, np.pi/4, 0],  # Camera 3 
]

# Load images from a folder and associate them with camera indices
def load_images_from_folder(folder, camera_count):
    camera_images = {i: [] for i in range(camera_count)}
    for i in range(camera_count):
        camera_folder = os.path.join(folder, f'camera_{i}')
        if os.path.exists(camera_folder):
            for filename in os.listdir(camera_folder):
                if filename.endswith(('.jpg', '.jpeg', '.png')):
                    img_path = os.path.join(camera_folder, filename)
                    img = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
                    if img is not None:
                        camera_images[i].append(img)
    return camera_images

# Generate synthetic images simulating a sphere
def generate_synthetic_images(camera_positions, num_voxels):
    synthetic_images = {i: [] for i in range(len(camera_positions))}
    sphere_radius = 1  # Radius of the sphere in the physical size

    for cam_index, pos in enumerate(camera_positions):
        for angle in np.linspace(0, 2 * np.pi, 12):
            img = np.zeros((num_voxels, num_voxels), dtype=np.float32)
            for x in range(num_voxels):
                for y in range(num_voxels):
                    norm_x = (x - num_voxels / 2) / (num_voxels / 2)
                    norm_y = (y - num_voxels / 2) / (num_voxels / 2)
                    distance = np.sqrt(norm_x**2 + norm_y**2)
                    if distance < sphere_radius:  # Inside the sphere
                        img[y, x] = sphere_radius - distance  # Simulate shading based on distance
            synthetic_images[cam_index].append(img)
    
    return synthetic_images

# Initialize 3D volume (voxel grid)
def initialize_volume(size):
    return np.zeros((size, size, size), dtype=np.float32)

def initialize_volume_with_sphere(size, radius):
    volume = np.zeros((size, size, size), dtype=np.float32)
    center = size // 2  # Center of the volume

    # Create a sphere within the volume
    for x in range(size):
        for y in range(size):
            for z in range(size):
                # Calculate the distance from the center
                distance = np.sqrt((x - center) ** 2 + (y - center) ** 2 + (z - center) ** 2)
                if distance < radius:
                    volume[x, y, z] = 1.0  # Set the voxel to 1 (inside the sphere)

    return volume

def rotation_matrix(azimuth, polar):
    cos_az = np.cos(azimuth)
    sin_az = np.sin(azimuth)
    cos_pol = np.cos(polar)
    sin_pol = np.sin(polar)

    rotation_yaw = np.array([[cos_az, -sin_az, 0],
                              [sin_az, cos_az, 0],
                              [0, 0, 1]])

    rotation_pitch = np.array([[1, 0, 0],
                                [0, cos_pol, -sin_pol],
                                [0, sin_pol, cos_pol]])

    return rotation_pitch @ rotation_yaw

# Projection function
def project(volume, position, azimuth, polar):
    rotation = rotation_matrix(azimuth, polar)
    transformation_matrix = np.eye(4)
    transformation_matrix[:3, :3] = rotation
    transformation_matrix[:3, 3] = position

    projected_image = np.zeros((num_voxels, num_voxels), dtype=np.float32)

    for x in range(volume.shape[0]):
        for y in range(volume.shape[1]):
            for z in range(volume.shape[2]):
                # Scale voxel position by voxel_size
                point_3d = np.array([x * voxel_size, y * voxel_size, z * voxel_size, 1])
                transformed_point = transformation_matrix @ point_3d

                if transformed_point[2] > 0:  # Avoid division by zero
                    # Project 3D point to 2D image plane
                    x_proj = int((transformed_point[0] / transformed_point[2]) * camera_matrix[0, 0] + camera_matrix[0, 2])
                    y_proj = int((transformed_point[1] / transformed_point[2]) * camera_matrix[1, 1] + camera_matrix[1, 2])

                    if 0 <= x_proj < projected_image.shape[1] and 0 <= y_proj < projected_image.shape[0]:
                        projected_image[y_proj, x_proj] += volume[x, y, z]

    return projected_image

# Update function based on ART
def update_volume(volume, observed, projected):
    observed_resized = cv2.resize(observed, (num_voxels, num_voxels))
    residual = observed_resized.astype(np.float32) - projected.astype(np.float32)

    # Debug: Check values of residual
    # print("Residual values:", residual)

    residual = np.clip(residual, -255, 255)
    volume += alpha * residual[:, :, np.newaxis]
    volume = np.clip(volume, 0, 255)

    return volume

# Main reconstruction function
def reconstruct(camera_images, sphere_radius):
    volume = initialize_volume_with_sphere(num_voxels, sphere_radius)
    if zeros:
        volume = initialize_volume(num_voxels)

    for i in range(num_iterations):
        for cam_index, images in camera_images.items():
            for img in images:
                resized_img = cv2.resize(img, (num_voxels, num_voxels))
                projected = project(volume, camera_positions[cam_index][:3], camera_positions[cam_index][3], camera_positions[cam_index][4])

                # Debug: Visualize projected images and volume updates
                if i % 5 == 10:  # Every 5 iterations
                    plt.imshow(projected, cmap='gray')
                    plt.title(f'Projected Image from Camera {cam_index} - Iteration {i}')
                    plt.show()
                    print(f"Volume after iteration {i}:\n", volume)

                volume = update_volume(volume, resized_img, projected)

    return volume


def generate_sphere_vertices(radius, num_points=100):
    phi = np.linspace(0, np.pi, num_points)
    theta = np.linspace(0, 2 * np.pi, num_points)
    phi, theta = np.meshgrid(phi, theta)

    x = radius * np.sin(phi) * np.cos(theta)
    y = radius * np.sin(phi) * np.sin(theta)
    z = radius * np.cos(phi)

    return x.flatten(), y.flatten(), z.flatten()

def visualize_volume(volume, camera_positions):
    verts, faces, _, _ = measure.marching_cubes(volume, level=0.5)
    scale_factor = voxel_size / 2  # Scale vertices for physical size
    verts *= scale_factor

    fig = plt.figure()
    ax = fig.add_subplot(111, projection='3d')
    ax.plot_trisurf(verts[:, 0], verts[:, 1], verts[:, 2], triangles=faces, color='cyan', linewidth=0.1, antialiased=True, label='Reconstructed Volume')
    if use_synthetic_images:
        # Add synthetic sphere to the visualization
        sphere_x, sphere_y, sphere_z = generate_sphere_vertices(sphere_radius)
        ax.scatter(sphere_x, sphere_y, sphere_z, color='red', alpha=0.05, label='Synthetic Sphere', s=1)
        ax.set_title('Reconstructed 3D Object with Synthetic Sphere')
    else:
        ax.set_title('Reconstructed 3D Object')

    def draw_camera_fov(ax, position, azimuth, polar):
        fov_radius = 2 * scale_factor
        fov_vectors = np.array([[fov_radius, 0, 0], [0, fov_radius, 0], [0, 0, -fov_radius]])
        rotation = rotation_matrix(azimuth, polar)
        rotated_vectors = fov_vectors @ rotation.T
        fov_corners = position[:3] + rotated_vectors

        for corner in fov_corners:
            ax.plot([position[0], corner[0]], [position[1], corner[1]], [position[2], corner[2]], color='orange')

    for i in range(len(camera_positions)):
        ax.scatter(camera_positions[i][0], camera_positions[i][1], camera_positions[i][2], marker='.', label="Camera " + str(i + 1))
        draw_camera_fov(ax, camera_positions[i][:3], camera_positions[i][3], camera_positions[i][4])

    ax.set_xlabel('X (Physical Size)')
    ax.set_ylabel('Y (Physical Size)')
    ax.set_zlabel('Z (Physical Size)')
    ax.legend(loc='center left', bbox_to_anchor=(1, 0.5))
    plt.show()

# Main execution
if __name__ == "__main__":
    use_synthetic_images = True  # Set to False to use local images
    zeros = False # Set to False to use spherical initial guess
    folder_path = 'C:/Users/jared/OneDrive/Desktop/GPOE2025/Tomography_Main/Tomography/3dtest/images_fake'  # Replace with your folder path

    camera_count = len(camera_positions)  # Number of cameras
    if use_synthetic_images:
        synthetic_images = generate_synthetic_images(camera_positions, num_voxels)
    else:
        synthetic_images = load_images_from_folder(folder_path, camera_count)

    if synthetic_images:
        sphere_radius = 5  # Define your desired sphere radius
        volume = reconstruct(synthetic_images, sphere_radius)
        visualize_volume(volume, camera_positions)
    else:
        print("No images generated or found.")
