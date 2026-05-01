import { Composition } from "remotion";
import {
  SubtitleWithImages,
  subtitleSchema,
  defaultSubtitleProps,
} from "./SubtitleWithImages";
import { realProps } from "./realCues";
import { realPropsV3 } from "./realCuesV3";
import { realPropsV4 } from "./realCuesV4";
import { realPropsV5 } from "./realCuesV5";
import { Promo } from "./Promo";

const noImageProps = { ...realProps, disableImages: true };

export const Root: React.FC = () => {
  return (
    <>
      <Composition
        id="PublishVideo14"
        component={SubtitleWithImages}
        durationInFrames={realProps.durationInFrames}
        fps={30}
        width={1260}
        height={1680}
        schema={subtitleSchema}
        defaultProps={realProps}
      />
      <Composition
        id="PublishVideo14NoImages"
        component={SubtitleWithImages}
        durationInFrames={realProps.durationInFrames}
        fps={30}
        width={1260}
        height={1680}
        schema={subtitleSchema}
        defaultProps={noImageProps}
      />
      <Composition
        id="PublishVideo14V3"
        component={SubtitleWithImages}
        durationInFrames={realPropsV3.durationInFrames}
        fps={30}
        width={1260}
        height={1680}
        schema={subtitleSchema}
        defaultProps={realPropsV3}
      />
      <Composition
        id="PublishVideo14V4"
        component={SubtitleWithImages}
        durationInFrames={realPropsV4.durationInFrames}
        fps={30}
        width={1260}
        height={1680}
        schema={subtitleSchema}
        defaultProps={realPropsV4}
      />
      <Composition
        id="PublishVideo14V5"
        component={SubtitleWithImages}
        durationInFrames={realPropsV5.durationInFrames}
        fps={30}
        width={1080}
        height={1920}
        schema={subtitleSchema}
        defaultProps={realPropsV5}
      />
      <Composition
        id="SubtitleWithImagesDemo"
        component={SubtitleWithImages}
        durationInFrames={defaultSubtitleProps.durationInFrames}
        fps={30}
        width={1080}
        height={1920}
        schema={subtitleSchema}
        defaultProps={defaultSubtitleProps}
      />
      <Composition
        id="Promo"
        component={Promo}
        durationInFrames={1665}
        fps={30}
        width={1080}
        height={1920}
      />
    </>
  );
};
