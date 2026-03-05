import React from 'react';
import { registerRoot, Composition } from 'remotion';
import { GlitchTransition } from './compositions/GlitchTransition';
import { WaveformVisualizer } from './compositions/WaveformVisualizer';
import { SocialCard } from './compositions/SocialCard';
import { LowerThird } from './compositions/LowerThird';
import { TitleCard } from './compositions/TitleCard';

const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="GlitchTransition"
        component={GlitchTransition}
        durationInFrames={21}
        fps={30}
        width={1920}
        height={1080}
      />
      <Composition
        id="WaveformVisualizer"
        component={WaveformVisualizer}
        durationInFrames={300}
        fps={30}
        width={1920}
        height={1080}
        defaultProps={{
          title: 'Pulse Check Daily',
          btcPrice: '$72,285',
          date: '2026-03-05',
          durationInFrames: 300,
        }}
      />
      <Composition
        id="SocialCard"
        component={SocialCard}
        durationInFrames={150}
        fps={30}
        width={1920}
        height={1080}
        defaultProps={{
          handle: 'saylor',
          text: 'I am buying bitcoin right now. Are you?',
          likes: 65156,
          retweets: 6918,
          durationInFrames: 150,
        }}
      />
      <Composition
        id="LowerThird"
        component={LowerThird}
        durationInFrames={180}
        fps={30}
        width={1920}
        height={1080}
        defaultProps={{
          channelName: 'Simply Bitcoin',
          speakerName: 'Nico Moran',
          durationInFrames: 180,
        }}
      />
      <Composition
        id="TitleCard"
        component={TitleCard}
        durationInFrames={120}
        fps={30}
        width={1920}
        height={1080}
        defaultProps={{
          title: 'Saylor Says You Don\'t Want Bitcoin',
          date: '2026-03-05',
          durationInFrames: 120,
        }}
      />
    </>
  );
};

registerRoot(RemotionRoot);
