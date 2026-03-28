import { Config } from "@remotion/cli/config";

Config.setVideoImageFormat("jpeg");
Config.setOverwriteOutput(true);
Config.setChromiumMultiProcessOnLinux(true);
Config.setTimeoutInMilliseconds(60000);
Config.setPixelFormat("yuv420p");
