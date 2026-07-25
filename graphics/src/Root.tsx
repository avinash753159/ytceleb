import React from 'react';
import {Composition, getInputProps} from 'remotion';
import {
  KenBurns, ListReveal, LowerThird, PersonCard, SplitCompare, StatCard,
} from './components';
import {
  BarsRise, EraCard, IconBurst, MacroApp, PeopleRow, SiteZoom, TypeOn,
} from './v5cards';

// One composition per treatment graphic. Duration/fps come from input props
// (--props=./props.json; inline JSON is broken on Windows shells).
// props.json shape: {"durationInFrames": 120, "fps": 30, ...component props}

const P = getInputProps() as Record<string, unknown>;
const FPS = (P.fps as number) ?? 30;
const DUR = (P.durationInFrames as number) ?? 150;
const W = 1920;
const H = 1080;

export const Root: React.FC = () => (
  <>
    <Composition id="ListReveal" component={ListReveal as React.FC}
      durationInFrames={DUR} fps={FPS} width={W} height={H}
      defaultProps={{items: [{text: 'Item one', atMs: 0}]}} />
    <Composition id="StatCard" component={StatCard as React.FC}
      durationInFrames={DUR} fps={FPS} width={W} height={H}
      defaultProps={{value: '20', label: 'pounds of muscle'}} />
    <Composition id="PersonCard" component={PersonCard as React.FC}
      durationInFrames={DUR} fps={FPS} width={W} height={H}
      defaultProps={{imageSrc: '', name: 'Name', role: 'Role'}} />
    <Composition id="LowerThird" component={LowerThird as React.FC}
      durationInFrames={DUR} fps={FPS} width={W} height={H}
      defaultProps={{title: 'Title'}} />
    <Composition id="SplitCompare" component={SplitCompare as React.FC}
      durationInFrames={DUR} fps={FPS} width={W} height={H}
      defaultProps={{leftSrc: '', rightSrc: '', leftLabel: '38',
                     rightLabel: '47'}} />
    <Composition id="KenBurns" component={KenBurns as React.FC}
      durationInFrames={DUR} fps={FPS} width={W} height={H}
      defaultProps={{src: ''}} />
    <Composition id="SiteZoom" component={SiteZoom as React.FC}
      durationInFrames={DUR} fps={FPS} width={W} height={H}
      defaultProps={{src: ''}} />
    <Composition id="IconBurst" component={IconBurst as React.FC}
      durationInFrames={DUR} fps={FPS} width={W} height={H}
      defaultProps={{center: '💪'}} />
    <Composition id="PeopleRow" component={PeopleRow as React.FC}
      durationInFrames={DUR} fps={FPS} width={W} height={H}
      defaultProps={{}} />
    <Composition id="BarsRise" component={BarsRise as React.FC}
      durationInFrames={DUR} fps={FPS} width={W} height={H}
      defaultProps={{bars: [{label: 'A', value: 10}]}} />
    <Composition id="TypeOn" component={TypeOn as React.FC}
      durationInFrames={DUR} fps={FPS} width={W} height={H}
      defaultProps={{text: 'How does Ryan Reynolds train?'}} />
    <Composition id="EraCard" component={EraCard as React.FC}
      durationInFrames={DUR} fps={FPS} width={W} height={H}
      defaultProps={{year: '2016', title: 'Deadpool'}} />
    <Composition id="MacroApp" component={MacroApp as React.FC}
      durationInFrames={DUR} fps={FPS} width={W} height={H}
      defaultProps={{}} />
  </>
);
