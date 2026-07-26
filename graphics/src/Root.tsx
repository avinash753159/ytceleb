import React from 'react';
import {Composition, getInputProps} from 'remotion';
import {
  KenBurns, ListReveal, LowerThird, PersonCard, SplitCompare, StatCard,
} from './components';
import {
  BarsRise, EraCard, IconBurst, MacroApp, PeopleRow, SiteZoom, TypeOn,
} from './v5cards';
import {
  BigCounter, CalendarGrid, ClockRing, DonutGauge, GramsBar, PlateCounter,
  RangeSplit, StepsRing, TicketStub, YearsTimeline,
} from './v6cards';
import {
  ArrowCallout, Checklist, IndexCards, InstaCard, PhotoTiles, StepCards,
} from './v7cards';
import {CommentPrompt, LikeSubBug, SubscribeCard} from './v8cards';
import {ChapterChip, Checklist2, PhotoBurst, PhotoTiles2,
        StepCards2} from './v9cards';
import {ExerciseCard} from './v10cards';

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
    <Composition id="DonutGauge" component={DonutGauge as React.FC}
      durationInFrames={DUR} fps={FPS} width={W} height={H}
      defaultProps={{pct: 90, title: 'x'}} />
    <Composition id="ClockRing" component={ClockRing as React.FC}
      durationInFrames={DUR} fps={FPS} width={W} height={H}
      defaultProps={{fromH: 7, toH: 9, title: 'x'}} />
    <Composition id="CalendarGrid" component={CalendarGrid as React.FC}
      durationInFrames={DUR} fps={FPS} width={W} height={H}
      defaultProps={{activeDays: 6, title: 'x'}} />
    <Composition id="PlateCounter" component={PlateCounter as React.FC}
      durationInFrames={DUR} fps={FPS} width={W} height={H}
      defaultProps={{display: 'x', title: 'x'}} />
    <Composition id="GramsBar" component={GramsBar as React.FC}
      durationInFrames={DUR} fps={FPS} width={W} height={H}
      defaultProps={{icon: 'x', display: 'x', title: 'x'}} />
    <Composition id="TicketStub" component={TicketStub as React.FC}
      durationInFrames={DUR} fps={FPS} width={W} height={H}
      defaultProps={{big: 'x', small: 'x', title: 'x'}} />
    <Composition id="BigCounter" component={BigCounter as React.FC}
      durationInFrames={DUR} fps={FPS} width={W} height={H}
      defaultProps={{from: 0, to: 100, title: 'x'}} />
    <Composition id="YearsTimeline" component={YearsTimeline as React.FC}
      durationInFrames={DUR} fps={FPS} width={W} height={H}
      defaultProps={{years: [{y: 'x', label: 'x'}], title: 'x'}} />
    <Composition id="RangeSplit" component={RangeSplit as React.FC}
      durationInFrames={DUR} fps={FPS} width={W} height={H}
      defaultProps={{left: 'x', right: 'x', leftSub: 'x', rightSub: 'x',
                     title: 'x'}} />
    <Composition id="StepsRing" component={StepsRing as React.FC}
      durationInFrames={DUR} fps={FPS} width={W} height={H}
      defaultProps={{display: 'x', title: 'x'}} />
    <Composition id="IndexCards" component={IndexCards as React.FC}
      durationInFrames={DUR} fps={FPS} width={W} height={H}
      defaultProps={{cards: [{text: 'x', atMs: 0}]}} />
    <Composition id="Checklist" component={Checklist as React.FC}
      durationInFrames={DUR} fps={FPS} width={W} height={H}
      defaultProps={{items: [{text: 'x', atMs: 0}]}} />
    <Composition id="PhotoTiles" component={PhotoTiles as React.FC}
      durationInFrames={DUR} fps={FPS} width={W} height={H}
      defaultProps={{tiles: [{src: '', label: 'x', atMs: 0}]}} />
    <Composition id="StepCards" component={StepCards as React.FC}
      durationInFrames={DUR} fps={FPS} width={W} height={H}
      defaultProps={{steps: [{text: 'x', atMs: 0}]}} />
    <Composition id="ArrowCallout" component={ArrowCallout as React.FC}
      durationInFrames={DUR} fps={FPS} width={W} height={H}
      defaultProps={{name: 'x'}} />
    <Composition id="InstaCard" component={InstaCard as React.FC}
      durationInFrames={DUR} fps={FPS} width={W} height={H}
      defaultProps={{handle: 'x', name: 'x', bio: 'x', avatarSrc: ''}} />
    <Composition id="SubscribeCard" component={SubscribeCard as React.FC}
      durationInFrames={DUR} fps={FPS} width={W} height={H}
      defaultProps={{}} />
    <Composition id="CommentPrompt" component={CommentPrompt as React.FC}
      durationInFrames={DUR} fps={FPS} width={W} height={H}
      defaultProps={{a: 'x', b: 'y'}} />
    <Composition id="LikeSubBug" component={LikeSubBug as React.FC}
      durationInFrames={DUR} fps={FPS} width={W} height={H}
      defaultProps={{}} />
    <Composition id="PhotoTiles2" component={PhotoTiles2 as React.FC}
      durationInFrames={DUR} fps={FPS} width={W} height={H}
      defaultProps={{title: 'x', tiles: [{src: '', label: 'x', atMs: 0}]}} />
    <Composition id="PhotoBurst" component={PhotoBurst as React.FC}
      durationInFrames={DUR} fps={FPS} width={W} height={H}
      defaultProps={{label: 'x',
                     satellites: [{src: '', label: 'x', atMs: 0}]}} />
    <Composition id="StepCards2" component={StepCards2 as React.FC}
      durationInFrames={DUR} fps={FPS} width={W} height={H}
      defaultProps={{title: 'x', steps: [{text: 'x', atMs: 0}]}} />
    <Composition id="Checklist2" component={Checklist2 as React.FC}
      durationInFrames={DUR} fps={FPS} width={W} height={H}
      defaultProps={{title: 'x', items: [{text: 'x', atMs: 0}]}} />
    <Composition id="ChapterChip" component={ChapterChip as React.FC}
      durationInFrames={DUR} fps={FPS} width={W} height={H}
      defaultProps={{part: 'PART 1', title: 'x'}} />
    <Composition id="ExerciseCard" component={ExerciseCard as React.FC}
      durationInFrames={DUR} fps={FPS} width={W} height={H}
      defaultProps={{name: 'x', img0: '', img1: ''}} />
  </>
);
