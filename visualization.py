import numpy as np
import open3d as o3d
import pytransform3d.rotations as pr
import pytransform3d.transformations as pt
import pytransform3d.trajectories as ptr
from pytransform3d import urdf
import warnings


def figure():
    return Figure()


def plot_basis(figure, R, p=np.zeros(3), s=1.0):
    A2B = pt.transform_from(R=R, p=p)
    frame = Frame(A2B, s=s)
    frame.add_frame(figure)


def plot_trajectory(figure, P, show_direction=True, n_frames=10, s=1.0, c=[0, 0, 0]):
    H = ptr.matrices_from_pos_quat(P)
    assert not show_direction, "not implemented yet"
    trajectory = Trajectory(H, show_direction, n_frames, s, c)
    trajectory.add_trajectory(figure)


class Figure:
    def __init__(self):
        self.visualizer = o3d.visualization.Visualizer()
        self.visualizer.create_window()

    def add_geometry(self, geometry):
        self.visualizer.add_geometry(geometry)

    def set_line_width(self, line_width):
        self.visualizer.get_render_option().line_width = line_width
        self.visualizer.update_renderer()

    def view_init(self, azim=-60, elev=30):
        vc = self.visualizer.get_view_control()
        pcp = vc.convert_to_pinhole_camera_parameters()
        distance = np.linalg.norm(pcp.extrinsic[:3, 3])
        R_azim_elev_0_world2camera = np.array([
            [0, 1, 0],
            [0, 0, -1],
            [-1, 0, 0]])
        R_azim_elev_0_camera2world = R_azim_elev_0_world2camera.T
        # azimuth and elevation are defined in world frame
        R_azim = pr.active_matrix_from_angle(2, np.deg2rad(azim))
        R_elev = pr.active_matrix_from_angle(1, np.deg2rad(-elev))
        R_elev_azim_camera2world = R_azim.dot(R_elev).dot(R_azim_elev_0_camera2world)
        pcp.extrinsic = pt.transform_from(  # world2camera
            R=R_elev_azim_camera2world.T,
            p=[0, 0, distance])
        vc.convert_from_pinhole_camera_parameters(pcp)

    def show(self):
        self.visualizer.run()
        self.visualizer.destroy_window()


class Frame:
    def __init__(self, A2B, label=None, s=1.0):
        self.A2B = A2B
        self.label = label
        if label is not None:
            warnings.warn(
                "This viewer does not support text. Frame label "
                "will be ignored.")
        self.s = s

    def set_data(self, A2B, label=None):
        raise NotImplementedError()

    def add_frame(self, figure):
        frame = o3d.geometry.TriangleMesh.create_coordinate_frame(
            size=self.s)
        frame.transform(self.A2B)
        figure.add_geometry(frame)


class Trajectory:
    def __init__(self, H, show_direction=True, n_frames=10, s=1.0, c=[0, 0, 0]):
        self.H = H
        self.show_direction = show_direction
        self.n_frames = n_frames
        self.s = s
        self.c = c

    def set_data(self, H, label=None):
        raise NotImplementedError()

    def add_trajectory(self, figure):
        points = self.H[:, :3, 3]
        lines = np.hstack((np.arange(len(points) - 1)[:, np.newaxis],
                           np.arange(1, len(points))[:, np.newaxis]))
        line_set = o3d.geometry.LineSet(
            points=o3d.utility.Vector3dVector(points),
            lines=o3d.utility.Vector2iVector(lines))
        colors = [self.c for _ in range(len(lines))]
        line_set.colors = o3d.utility.Vector3dVector(colors)
        figure.add_geometry(line_set)

        key_frames_indices = np.linspace(
            0, len(self.H) - 1, self.n_frames, dtype=np.int)
        for i, key_frame_idx in enumerate(key_frames_indices):
            frame = Frame(self.H[key_frame_idx], s=self.s)
            frame.add_frame(figure)


def show_urdf_transform_manager(
        figure, tm, frame, collision_objects=False, visuals=False,
        frames=False, whitelist=None, s=1.0, c=None):
    if collision_objects:
        if hasattr(tm, "collision_objects"):
            _add_objects(figure, tm, tm.collision_objects, frame, c)
    if visuals:
        if hasattr(tm, "visuals"):
            _add_objects(figure, tm, tm.visuals, frame, c)
    if frames:
        for node in tm.nodes:
            _add_frame(figure, tm, node, frame, whitelist, s)


def _add_objects(figure, tm, objects, frame, c=None):
    for obj in objects:
        obj.show(figure, tm, frame, c)


def _add_frame(figure, tm, from_frame, to_frame, whitelist=None, s=1.0):
    if whitelist is not None and from_frame not in whitelist:
        return
    A2B = tm.get_transform(from_frame, to_frame)
    frame = Frame(A2B, s=s)
    frame.add_frame(figure)


def box_show(self, figure, tm, frame, c=None):
    raise NotImplementedError()


urdf.Box.show = box_show


def sphere_show(self, figure, tm, frame, c=None):
    raise NotImplementedError()


urdf.Sphere.show = sphere_show


def cylinder_show(self, figure, tm, frame, c=None):
    raise NotImplementedError()


urdf.Cylinder.show = cylinder_show


def mesh_show(self, figure, tm, frame, c=None):
    if self.mesh_path is None:
        print("No mesh path given")
        return
    A2B = tm.get_transform(self.frame, frame)

    scale = self.scale
    mesh = o3d.io.read_triangle_mesh(self.filename)
    mesh.vertices = o3d.utility.Vector3dVector(np.asarray(mesh.vertices) * scale)
    mesh.transform(A2B)
    if c is not None:
        n_vertices = len(mesh.vertices)
        colors = np.zeros((n_vertices, 3))
        colors[:] = c
        mesh.vertex_colors = o3d.utility.Vector3dVector(colors)
    figure.add_geometry(mesh)


urdf.Mesh.show = mesh_show
