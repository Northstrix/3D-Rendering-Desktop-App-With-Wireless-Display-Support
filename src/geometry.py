from multiprocessing import Process, Queue
import math
import numpy as np
import time

def time_me(f):
	'''Decorator function to time functions' runtime in ms'''
	def wrapper(*args, **kwargs):
		start = time.time()
		res = f(*args, **kwargs)
		print(f'function: {f.__name__} took {(time.time()-start)*1000:.4f}ms')
		return res
	return wrapper

class Geometry:
	'''
	'''
	def __init__(self, canvas_width: int, canvas_height: int) -> None:
		'''
		'''
		self.CANVAS_WIDTH = canvas_width
		self.CANVAS_HEIGHT = canvas_height
		self.OBJECT_SCALE = 2500 # Maybe make this dynamic depending on the object size
		
		self._obj_position = [canvas_width//2, canvas_height//2]
		self._zoom = 20
		self._angle_x = 0
		self._angle_y = 0
		self._angle_z = 0
		self._faces = []
		self._verticies = {}

		# Thread safe queue for the mutiple cores to be able to split the work
		self.pts_q = Queue()

	def update_position(self, x: int, y: int) -> None:
		'''Update x, y position of the object'''
		self._obj_position[0] += x
		self._obj_position[1] += y

	def __trasform_and_package_points(self, idx_list, pt_list, rot_x, rot_y, rot_z):
		'''Transforms a list of points and packages them into index:point pairs for drawing'''
		projected_points = {}
		for idx, pt in zip(idx_list, pt_list):
			x, y = self.__transform_point(pt, rot_x, rot_y, rot_z)
			projected_points[idx] = [x, y]
		self.pts_q.put(projected_points)
		
	@time_me
	def transform_object(self) -> dict:
		'''Retur the points of the object transformed according to the current position'''
		rot_x, rot_y, rot_z = self.__calculate_rot_matrix()

		# Going to slice these and distribute them on the available processes
		indexes_list = list(self._verticies.keys())
		points_list = list(self._verticies.values())
		
		# More than 4 cores is just useless
		NUM_PROCESSES = 4 #os.cpu_count()
		SEGMENT_LEN = len(indexes_list)//NUM_PROCESSES

		for i in range(NUM_PROCESSES):
			# The last one shall grab all the points left (difference is an extra point)
			if i == NUM_PROCESSES-1:
				idx = indexes_list[i*SEGMENT_LEN:]
				pts = points_list[i*SEGMENT_LEN:]
			else:
				idx = indexes_list[i*SEGMENT_LEN:(i+1)*SEGMENT_LEN]
				pts = points_list[i*SEGMENT_LEN:(i+1)*SEGMENT_LEN]

			Process(target=self.__trasform_and_package_points, args=([idx, pts, rot_x, rot_y, rot_z])).start()
		
		all_points = {}
		for _ in range(NUM_PROCESSES):
			all_points.update(self.pts_q.get())

		return all_points
	
	@property
	def faces(self) -> list:
		'''Get the faces formed between the points'''
		return self._faces

	@property
	def zoom(self):
		'''Get the current zoom value'''
		return self._zoom

	def set_zoom(self, zoom: int) -> None:
		'''Set the new zoom value'''
		self._zoom = zoom

	def reset_rotation(self, x: float = None, y: float = None, z: float = None) -> None:
		'''Reset the rotation to a specific position else to 0'''
		self._angle_x = 0 if x is None else x
		self._angle_y = 0 if y is None else y
		self._angle_z = 0 if z is None else z

	def __transform_point(self, point, rotation_x, rotation_y, rotation_z) -> 'tuple(int, int)':
		'''Rotate the point in 3axis according to the provided rotation matrices'''
		# Rotate point on the Y, X, and Z axis respectively
		rotated_2d = np.matmul(rotation_y, point)
		rotated_2d = np.matmul(rotation_x, rotated_2d)
		rotated_2d = np.matmul(rotation_z, rotated_2d)

		# Project 3D point on 2D plane
		z = 0.5 / (self._zoom - rotated_2d[2][0])
		projection_matrix = np.array(((z, 0, 0), (0, z, 0)))
		projected_2d = np.matmul(projection_matrix, rotated_2d)

		x = int(projected_2d[0][0] * self.OBJECT_SCALE) + self._obj_position[0]

		# The (-) sign in the Y is because the canvas' Y axis starts
		# from Top to Bottom, so without the (-) sign, our objects
		# would be presented upside down
		y = -int(projected_2d[1][0] * self.OBJECT_SCALE) + self._obj_position[1]

		return x, y

	def __calculate_rot_matrix(self) -> 'tuple(np.array, np.array, np.array)':
		'''
		Calculate the rotation matrices on X, Y, and Z axis 
		that correspond to the current requested rotation
		'''
		rotation_x = np.array(
			(
				(1,               0        ,               0         ),
				(0, math.cos(self._angle_x), -math.sin(self._angle_x)),
				(0, math.sin(self._angle_x),  math.cos(self._angle_x))
			)
		)

		rotation_y = np.array(
			(
				(math.cos(self._angle_y), 0, -math.sin(self._angle_y)),
				(            0          , 1,             0           ),
		        (math.sin(self._angle_y), 0,  math.cos(self._angle_y))
			)
		)

		rotation_z = np.array(
			(
				(math.cos(self._angle_z), -math.sin(self._angle_z), 0),
			 	(math.sin(self._angle_z),  math.cos(self._angle_z), 0),
			 	(           0           ,              0          , 1)
			)
		)
		return rotation_x, rotation_y, rotation_z


if __name__ == '__main__':
    print("This is not the executable file, go to the 'main.py' file and run it instead!")