#ifndef IKRIG_IKRIGNODE_H
#define IKRIG_IKRIGNODE_H

#include <maya/MArrayDataHandle.h>
#include <maya/MFloatVector.h>
#include <maya/MMatrix.h>
#include <maya/MMatrixArray.h>
#include <maya/MPoint.h>
#include <maya/MPxNode.h>
#include <maya/MQuaternion.h>

class IKRigNode : public MPxNode {
 public:
  enum IKRigPart {
    IKRig_Hips,
    IKRig_Chest,
    IKRig_Neck,
    IKRig_Head,
    IKRig_LeftClavicle,
    IKRig_LeftShoulder,
    IKRig_LeftElbow,
    IKRig_LeftHand,
    IKRig_LeftUpLeg,
    IKRig_LeftLoLeg,
    IKRig_LeftFoot,
    IKRig_RightClavicle,
    IKRig_RightShoulder,
    IKRig_RightElbow,
    IKRig_RightHand,
    IKRig_RightUpLeg,
    IKRig_RightLoLeg,
    IKRig_RightFoot,
    IKRig_Count
  };

  IKRigNode();
  virtual ~IKRigNode();
  static void* creator();

  virtual MStatus compute(const MPlug& plug, MDataBlock& data);

  static MStatus initialize();
  static MTypeId id;
  static const MString kName;
  static MObject aOutTranslate;
  static MObject aOutRotate;
  static MObject aOutRotateX;
  static MObject aOutRotateY;
  static MObject aOutRotateZ;

  // Input Skeleton
  static MObject aInMatrix;
  static MObject aInBindPreMatrix;
  static MObject aTargetRestMatrix;
  static MObject aLeftLegTwistOffset;
  static MObject aRightLegTwistOffset;

 private:
  static void affects(const MObject& attribute);

  MStatus calculateLegIk(unsigned int upLeg, unsigned int loLeg, unsigned int foot,
                         const MMatrix& hips, float twist, MArrayDataHandle& hOutputTranslate,
                         MArrayDataHandle& hOutputRotate);

  MVector position(const MMatrix& m) { return MVector(m[3][0], m[3][1], m[3][2]); }

  void calculateTwoBoneIk(const MMatrix& root, const MMatrix& mid, const MMatrix& effector,
                          const MMatrix& target, const MVector& pv, MMatrix& ikA,
                          MMatrix& ikB);
  void twoBoneIk(const MVector& a, const MVector& b, const MVector& c, const MVector& d,
                 const MVector& t, const MVector& pv, MQuaternion& a_gr,
                 MQuaternion& b_gr);
  MStatus setOutput(MArrayDataHandle& hOutputTranslate, MArrayDataHandle& hOutputRotate,
                    unsigned int bodyPart, const MMatrix& matrix);
  float clamp(float inValue, float minValue, float maxValue) {
    if (inValue < minValue) {
      return minValue;
    }
    if (inValue > maxValue) {
      return maxValue;
    }
    return inValue;
  }

  MMatrixArray inputMatrix_;
  MMatrixArray inputBindPreMatrix_;
  MMatrixArray targetRestMatrix_;
  MMatrixArray outputDelta_;
};

#endif
