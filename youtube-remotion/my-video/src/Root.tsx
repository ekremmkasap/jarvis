import { Composition } from "remotion";
import { MainComposition } from "./components/MainComposition";
import storyboard from "./data/storyboard.json";

const totalFrames = storyboard.scenes.reduce((s: number, sc: any) => s + sc.durationFrames, 0);

export const RemotionRoot: React.FC = () => (
  <Composition
    id="MainVideo"
    component={MainComposition}
    durationInFrames={totalFrames || 180}
    fps={storyboard.fps || 30}
    width={1920}
    height={1080}
  />
);
