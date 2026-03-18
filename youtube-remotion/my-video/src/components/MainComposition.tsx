import React from "react";
import {
  AbsoluteFill, Sequence, Video, Audio, staticFile,
  useCurrentFrame, interpolate
} from "remotion";
import storyboard from "../data/storyboard.json";

export const MainComposition: React.FC = () => {
  const frame = useCurrentFrame();
  let offset = 0;

  return (
    <AbsoluteFill style={{ background: "#000" }}>
      {storyboard.scenes.map((scene: any) => {
        const from = offset;
        offset += scene.durationFrames;
        return (
          <Sequence key={scene.id} from={from} durationInFrames={scene.durationFrames}>
            {/* Video */}
            <AbsoluteFill>
              <Video
                src={staticFile("assets/videos/" + scene.videoFile)}
                style={{ width: "100%", height: "100%", objectFit: "cover" }}
              />
            </AbsoluteFill>

            {/* Audio */}
            <Audio src={staticFile("assets/audios/" + scene.audioFile)} />

            {/* Altyazi */}
            <AbsoluteFill style={{ justifyContent: "flex-end", padding: "60px" }}>
              <div style={{
                background: "rgba(0,0,0,0.65)",
                color: "#fff",
                fontSize: 36,
                fontFamily: "Arial, sans-serif",
                padding: "16px 24px",
                borderRadius: 12,
                maxWidth: "80%",
                textAlign: "center",
                alignSelf: "center",
                opacity: interpolate(frame - from, [0, 10], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" })
              }}>
                {scene.subtitle}
              </div>
            </AbsoluteFill>
          </Sequence>
        );
      })}
    </AbsoluteFill>
  );
};
