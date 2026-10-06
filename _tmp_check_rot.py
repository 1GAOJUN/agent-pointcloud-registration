import numpy as np
I=np.eye(4)
gt=np.load(r'D:\STUDY\darker\agent-pointcloud-registration\outputs\L2\gt_transform.npy')
coarse=np.load(r'D:\STUDY\darker\agent-pointcloud-registration\_coarse_sim.npy')
def re_deg(T1,T2):
    Rrel=T1[:3,:3].T@T2[:3,:3]
    c=np.clip((np.trace(Rrel)-1)/2,-1,1)
    return float(np.rad2deg(np.arccos(c)))
print('identity vs gt rot_err:', round(re_deg(I,gt),4))
print('coarse vs gt rot_err:', round(re_deg(coarse,gt),4))
