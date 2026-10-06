import sys, os, numpy as np, open3d as o3d
from PIL import Image, ImageDraw, ImageFont, Image as PILImage
sys.path.insert(0, 'src')
from evaluate import rotation_error_deg

W, H = 1920, 1080
SRC_COLOR = [1.0, 0.55, 0.10, 1.0]
TGT_COLOR = [0.10, 0.45, 0.95, 1.0]
BG = np.array([0.07, 0.08, 0.10, 1.0], dtype=np.float32)
POINT_SIZE = 6.0

def interp_T(T1, T2, t):
    R = (1-t)*T1[:3,:3] + t*T2[:3,:3]
    U,_,Vt = np.linalg.svd(R); R = U@Vt
    if np.linalg.det(R) < 0:
        U[:,-1]*=-1; R=U@Vt
    T = np.eye(4); T[:3,:3]=R; T[:3,3]=(1-t)*T1[:3,3]+t*T2[:3,3]
    return T

def rough_fitness(src_pts, tgt_pcd, T, n_sample=3000):
    pts = src_pts @ T[:3,:3].T + T[:3,3]
    rng = np.random.RandomState(42)
    sub = rng.choice(len(pts), min(n_sample,len(pts)), replace=False)
    kdt = o3d.geometry.KDTreeFlann(tgt_pcd)
    hit = 0
    for j in range(len(sub)):
        _,_,d2 = kdt.search_vector_3d(np.array(pts[sub[j]],dtype=np.float64).reshape(3,1),
                                       o3d.geometry.KDTreeSearchParamHybrid(radius=0.5, max_nn=1))
        if len(d2)>0 and np.sqrt(d2[0])<0.1: hit+=1
    return hit/len(sub) if len(sub)>0 else 0.0

src = o3d.io.read_point_cloud('outputs/L2/source.ply')
tgt = o3d.io.read_point_cloud('outputs/L2/target.ply')
T_gt = np.load('outputs/L2/gt_transform.npy')
src_pts = np.asarray(src.points)
T0 = np.eye(4)
T_coarse = np.load('_coarse_sim.npy')
T_final = np.load('outputs/L2/est_transform.npy')

print('CHECK frame0 identity vs gt: rot_err = %.3f deg' % rotation_error_deg(T0, T_gt))
print('CHECK coarse vs gt:           rot_err = %.3f deg' % rotation_error_deg(T_coarse, T_gt))
print('CHECK final vs gt:           rot_err = %.4f deg' % rotation_error_deg(T_final, T_gt))

renderer = o3d.visualization.rendering.OffscreenRenderer(W, H)
scene = renderer.scene
renderer.setup_camera(4.0, [0.0, 0.0, 0.0], [0.707, -0.707, 0.0], [0, 0, 1])
scene.set_background(BG)

def add_pcd(pcd, T, name, color):
    p = o3d.geometry.PointCloud()
    p.points = o3d.utility.Vector3dVector(np.asarray(pcd.points) @ T[:3,:3].T + T[:3,3])
    mat = o3d.visualization.rendering.MaterialRecord()
    mat.shader = "default"
    mat.base_color = color
    mat.point_size = POINT_SIZE
    scene.add_geometry(name, p, mat)

def render_frame(T_src, stage, idx_label, out_png):
    scene.clear_geometry()
    add_pcd(tgt, T_gt, "target", TGT_COLOR)
    add_pcd(src, T_src, "source", SRC_COLOR)
    o3d_img = renderer.render_to_image()
    if o3d_img is None:
        raise RuntimeError("offscreen render returned None")
    # o3d image -> PIL
    rgb = o3d_img.convert_to_pil()
    re = rotation_error_deg(T_src, T_gt)
    pi = rough_fitness(src_pts, tgt, T_src)
    draw = ImageDraw.Draw(rgb)
    lines = [f"[{stage}]  {idx_label}",
             f"rot_err  = {re:9.3f} deg",
             f"fitness  = {pi:9.4f}"]
    y = 30
    for i, ln in enumerate(lines):
        col = (255, 220, 120) if i == 0 else (230, 230, 230)
        fs = 40 if i == 0 else 30
        try:
            fnt = ImageFont.truetype("arialbd.ttf" if i==0 else "arial.ttf", fs)
        except Exception:
            fnt = ImageFont.load_default()
        draw.text((40, y), ln, fill=col, font=fnt)
        y += 55 if i == 0 else 45
    draw.rectangle([20,20,W-20,H-20], outline=(80,80,80), width=2)
    rgb.save(out_png)
    print(f"  saved {out_png}  rot_err={re:.3f}  fitness={pi:.4f}")

os.makedirs('outputs/L2/visuals/preview', exist_ok=True)
render_frame(T0, "INITIAL", "frame 0  |  identity guess", 'outputs/L2/visuals/preview/P1_initial_identity.png')
render_frame(T_coarse, "COARSE", "coarse jump  |  RANSAC/SVD result", 'outputs/L2/visuals/preview/P2_coarse_jump.png')
T_mid = interp_T(T_coarse, T_final, 0.5)
render_frame(T_mid, "REFINE", "ICP mid-frame 50%", 'outputs/L2/visuals/preview/P3_icp_mid.png')
render_frame(T_final, "FINAL", "final aligned  |  ICP converged", 'outputs/L2/visuals/preview/P4_final_aligned.png')
print("PREVIEWS DONE")
