#!/usr/bin/env python3

import sys, math, struct

iqm_va_type = {
	0: "position",
	1: "texcoord",
	2: "normal",
	3: "tangent",
	4: "blendindexes",
	5: "blendweights",
	6: "color",
	8: "reserved", 9: "reserved", 10: "reserved", 11: "reserved",
	12: "reserved", 13: "reserved", 14: "reserved", 15: "reserved",
	16: "custom0",
	17: "custom1",
	18: "custom2",
	19: "custom3",
	20: "custom4",
	21: "custom5",
	22: "custom6",
	23: "custom7",
	24: "custom8",
	25: "custom9",
}

iqm_va_format = {
	0: 'byte',
	1: 'ubyte',
	2: 'short',
	3: 'ushort',
	4: 'int',
	5: 'uint',
	6: 'half',
	7: 'float',
	8: 'double',
}

def cstr(text, ofs):
	len = 0
	while text[ofs+len] != 0:
		len += 1
	return text[ofs:ofs+len].decode("utf-8", "ignore")

def optscale(scale):
	x, y, z = scale
	if abs(x - 1) > 0.0001: return x, y, z
	if abs(y - 1) > 0.0001: return x, y, z
	if abs(z - 1) > 0.0001: return x, y, z
	return ()

def fmtv(v): return " ".join(["%.9g" % x for x in v])
def fmtb(v): return " ".join(["%.9g" % (x/255.0) for x in v])
def fmtp(v): return " ".join(["%.9g" % x for x in v])

def dump_joints(file, text, num_joints, ofs_joints):
	file.seek(ofs_joints)
	jointlist = []
	for x in range(num_joints):
		joint = struct.unpack("<Ii10f", file.read(12*4))
		jointlist += (joint,)
	print()
	for joint in jointlist:
		name = cstr(text, joint[0])
		parent = joint[1]
		print("joint", name, parent)
	print()
	for joint in jointlist:
		pos = joint[2:5]
		rot = joint[5:9]
		scale = joint[9:12]
		print("pq", fmtp(pos + rot + optscale(scale)))

def load_poses(file, num_poses, ofs_poses):
	file.seek(ofs_poses)
	poselist = []
	for x in range(num_poses):
		pose = struct.unpack("<iI20f", file.read(22*4))
		poselist.append(pose)
	return poselist

def load_frames(file, num_frames, num_framechannels, ofs_frames):
	file.seek(ofs_frames)
	F = "<"+"H"*num_framechannels; S=2*num_framechannels
	framelist = []
	for x in range(num_frames):
		frame = struct.unpack(F, file.read(S))
		framelist.append(frame)
	return framelist

def dump_frame(poselist, frame):
	masktest = [0x01, 0x02, 0x04, 0x08, 0x10, 0x20, 0x40, 0x80, 0x100, 0x200]
	p = 0
	for pose in poselist:
		mask = pose[1]
		choffset = pose[2:2+10]
		chscale = pose[2+10:2+10+10]
		data = [x for x in choffset]
		for x in range(10):
			if mask & masktest[x]:
				data[x] += chscale[x] * frame[p]
				p += 1
			pos = data[0:3]
			rot = [x for x in data[3:7]]
			scale = [x for x in optscale(data[7:10])]
		print("pq", fmtp(pos + rot + scale))

def dump_anims(file, text, num_anims, ofs_anims, poses, frames):
	file.seek(ofs_anims)
	for x in range(num_anims):
		anim = struct.unpack("<3IfI", file.read(5*4))
		name = cstr(text, anim[0])
		first = anim[1]
		count = anim[2]
		print()
		print("animation", name)
		print("framerate %g" % anim[3])
		if anim[4]: print("loop")
		for y in range(first, first+count):
			print()
			print("frame")
			dump_frame(poses, frames[y])

def load_array(file, format, size, offset, count):
	if format != 1 and format != 7:
		print("can only handle ubyte and float arrays", file=sys.stderr)
		sys.exit(1)
	if format == 1: A="<"+"B"*size; S=1*size
	if format == 7: A="<"+"f"*size; S=4*size
	file.seek(offset)
	list = []
	for x in range(count):
		comp = struct.unpack(A, file.read(S))
		list.append(comp)
	return list

def load_verts(file, text, num_vertexarrays, num_vertexes, ofs_vertexarrays):
	file.seek(ofs_vertexarrays)
	print()
	custom = 16
	valist = []
	for x in range(num_vertexarrays):
		va = struct.unpack("<5I", file.read(5*4))
		valist += (va,)
	verts = [None] * (16+10)
	vafmt = [None] * (16+10)
	for type, flags, format, size, offset in valist:
		if type < 16:
			type_name = iqm_va_type[type]
		else:
			type_name = cstr(text, type - 16)
			type = custom
			custom = custom + 1
		vafmt[type] = format
		verts[type] = load_array(file, format, size, offset, num_vertexes)
		if type != 4 and format == 7: verts[type]
		if type >= 16: print("vertexarray", iqm_va_type[type], iqm_va_format[format], size, type_name)
		else: print("vertexarray", iqm_va_type[type], iqm_va_format[format], size)
	return vafmt, verts

def load_tris(file, num_triangles, ofs_triangles, ofs_adjacency):
	file.seek(ofs_triangles)
	tris = []
	for x in range(num_triangles):
		tri = struct.unpack("<3I", file.read(3*4))
		tris.append(tri)
	return tris

def dump_verts(vafmt, verts, first, count):
	for x in range(first, first+count):
		if verts[0]: print("vp", fmtv(verts[0][x]))
		if verts[2]: print("vn", fmtv(verts[2][x]))
		if verts[3]: print("vx", fmtv(verts[3][x]))
		if verts[1]: print("vt", fmtv(verts[1][x]))
		if verts[6]: print("vc", fmtb(verts[6][x]))
		if verts[4] and verts[5]:
			out = "vb"
			for y in range(4):
				if verts[5][x][y] > 0:
					out += " %d" % verts[4][x][y]
					out += " %.9g" % (verts[5][x][y]/255.0)
			print(out)
		for i in range(16, 16+10):
			if verts[i] and vafmt[i] == 1: print("v%d" % (i-16), fmtb(verts[i][x]))
			if verts[i] and vafmt[i] == 7: print("v%d" % (i-16), fmtv(verts[i][x]))

def dump_tris(tris, first, count, fv):
	for x in range(first, first+count):
		tri = tris[x]
		print("fm", tri[0]-fv, tri[1]-fv, tri[2]-fv)

def dump_meshes(file, text, num_meshes, ofs_meshes, vafmt, verts, tris):
	file.seek(ofs_meshes)
	for x in range(num_meshes):
		mesh = struct.unpack("<6I", file.read(6*4))
		name = cstr(text, mesh[0])
		material = cstr(text, mesh[1])
		v1, vnum, t1, tnum = mesh[2:]
		print()
		print("mesh", name)
		print("material", material)
		dump_verts(vafmt, verts, v1, vnum)
		dump_tris(tris, t1, tnum, v1)

def dump_iqm(file):
	hdr = struct.unpack("<16s27I", file.read(124));
	( magic, version, filesize, flags,
		num_text, ofs_text,
		num_meshes, ofs_meshes,
		num_vertexarrays, num_vertexes, ofs_vertexarrays,
		num_triangles, ofs_triangles, ofs_adjacency,
		num_joints, ofs_joints,
		num_poses, ofs_poses,
		num_anims, ofs_anims,
		num_frames, num_framechannels, ofs_frames, ofs_bounds,
		num_comment, ofs_comment,
		num_extensions, ofs_extensions ) = hdr

	if magic != b"INTERQUAKEMODEL\0":
		print("Not an IQM file (%s)", repr(magic), file=sys.stderr)
		sys.exit(1)

	if version != 2:
		print("Not an IQMv2 file.", file=sys.stderr)
		sys.exit(1)

	print("# Inter-Quake Export")

	file.seek(ofs_text)
	text = file.read(num_text);

	if ofs_joints:
		dump_joints(file, text, num_joints, ofs_joints)
	if ofs_vertexarrays:
		vafmt, verts = load_verts(file, text, num_vertexarrays, num_vertexes, ofs_vertexarrays)
	if ofs_triangles:
		tris = load_tris(file, num_triangles, ofs_triangles, ofs_adjacency)
	if ofs_meshes:
		dump_meshes(file, text, num_meshes, ofs_meshes, vafmt, verts, tris)
	poses = load_poses(file, num_poses, ofs_poses)
	frames = load_frames(file, num_frames, num_framechannels, ofs_frames)
	# bounds are auto-computed, no need to load
	dump_anims(file, text, num_anims, ofs_anims, poses, frames)

for arg in sys.argv[1:]:
	file = open(arg, "rb")
	dump_iqm(file)

