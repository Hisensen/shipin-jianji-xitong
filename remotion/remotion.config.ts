import { Config } from "@remotion/cli/config";

Config.setVideoImageFormat("jpeg");
Config.setOverwriteOutput(true);
Config.setConcurrency(4);
// Mac M 系列硬件 H264 编码器（VideoToolbox），单帧编码可省 2-3 倍
Config.setHardwareAcceleration("if-possible");
// Chromium 用 Metal 硬件 GL，渲染加速
Config.setChromiumOpenGlRenderer("angle");
// JPEG 质量稍降以加速（视觉差不多看不出来）
Config.setJpegQuality(85);
