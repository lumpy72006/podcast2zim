import { V as Vitest, T as TestProject, a as TestProjectConfiguration } from './reporters.d.BQ0wpUaj.js';

interface VitestPluginContext {
	vitest: Vitest;
	project: TestProject;
	injectTestProjects: (config: TestProjectConfiguration | TestProjectConfiguration[]) => Promise<TestProject[]>;
}

export type { VitestPluginContext as V };
