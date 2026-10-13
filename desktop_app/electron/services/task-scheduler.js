import { app } from 'electron';
import { spawn } from 'node:child_process';

const TASK_PREFIX = 'FinanceScraper_';
const RECOVERY_TASK_NAME = 'FinanceScraper_ScheduleRecovery';
const TASK_ID_PATTERN = /^sch_[a-f0-9]{32}$/;

function quoteCommandValue(value) {
    return `"${String(value).replaceAll('"', '\\"')}"`;
}

function scheduledApplicationArguments(appInstance, scheduleId) {
    if (appInstance.isPackaged) {
        return [`--scheduled-task=${scheduleId}`];
    }
    return [
        appInstance.getAppPath(),
        `--scheduled-task=${scheduleId}`,
    ];
}

function recoveryApplicationArguments(appInstance) {
    if (appInstance.isPackaged) {
        return ['--recover-schedules'];
    }
    return [
        appInstance.getAppPath(),
        '--recover-schedules',
    ];
}

function taskAction(appInstance, args) {
    return [
        quoteCommandValue(process.execPath),
        ...args.map(quoteCommandValue),
    ].join(' ');
}

function runScheduledTasksCommand(args) {
    return new Promise((resolve, reject) => {
        const child = spawn('schtasks.exe', args, {
            windowsHide: true,
            shell: false,
            stdio: ['ignore', 'pipe', 'pipe'],
        });
        let stdout = '';
        let stderr = '';
        child.stdout.setEncoding('utf8');
        child.stderr.setEncoding('utf8');
        child.stdout.on('data', (chunk) => {
            stdout = `${stdout}${chunk}`.slice(-8_000);
        });
        child.stderr.on('data', (chunk) => {
            stderr = `${stderr}${chunk}`.slice(-8_000);
        });
        child.once('error', reject);
        child.once('close', (code, signal) => {
            if (code !== 0) {
                reject(
                    new Error(
                        `Windows Task Scheduler failed (${code ?? signal}): ${stderr || stdout}`,
                    ),
                );
                return;
            }
            resolve({ stdout, stderr });
        });
    });
}

function configureMissedRunRecovery(taskName) {
    if (!/^[A-Za-z0-9_]+$/.test(taskName)) {
        throw new Error('Scheduled task name has an invalid format.');
    }
    const script = [
        '$ErrorActionPreference = \'Stop\';',
        '$settings = New-ScheduledTaskSettingsSet',
        '-StartWhenAvailable',
        '-MultipleInstances IgnoreNew',
        '-ExecutionTimeLimit (New-TimeSpan -Hours 2)',
        '-AllowStartIfOnBatteries',
        '-DontStopIfGoingOnBatteries;',
        `Set-ScheduledTask -TaskName '${taskName}' -Settings $settings | Out-Null`,
    ].join(' ');
    return new Promise((resolve, reject) => {
        const child = spawn(
            'powershell.exe',
            [
                '-NoProfile',
                '-NonInteractive',
                '-ExecutionPolicy',
                'Bypass',
                '-Command',
                script,
            ],
            {
                windowsHide: true,
                shell: false,
                stdio: ['ignore', 'pipe', 'pipe'],
            },
        );
        let stdout = '';
        let stderr = '';
        child.stdout.setEncoding('utf8');
        child.stderr.setEncoding('utf8');
        child.stdout.on('data', (chunk) => {
            stdout = `${stdout}${chunk}`.slice(-8_000);
        });
        child.stderr.on('data', (chunk) => {
            stderr = `${stderr}${chunk}`.slice(-8_000);
        });
        child.once('error', reject);
        child.once('close', (code, signal) => {
            if (code !== 0) {
                reject(
                    new Error(
                        `Could not enable missed-run recovery (${code ?? signal}): ${stderr || stdout}`,
                    ),
                );
                return;
            }
            resolve();
        });
    });
}

function scheduleTaskName(scheduleId) {
    if (!TASK_ID_PATTERN.test(scheduleId)) {
        throw new Error('Schedule ID has an invalid format.');
    }
    return `${TASK_PREFIX}${scheduleId}`;
}

function buildAction(appInstance, argumentsList) {
    return taskAction(appInstance, argumentsList);
}

export class WindowsTaskScheduler {
    constructor(appInstance = app) {
        this.app = appInstance;
    }

    async registerDaily(schedule) {
        if (process.platform !== 'win32') {
            throw new Error('Scheduled report delivery is available on Windows.');
        }
        const taskName = scheduleTaskName(schedule.schedule_id);
        if (!/^\d{2}:\d{2}$/.test(schedule.run_at)) {
            throw new Error('Schedule time must use local HH:MM format.');
        }
        const action = buildAction(
            this.app,
            scheduledApplicationArguments(this.app, schedule.schedule_id),
        );
        await runScheduledTasksCommand([
            '/Create',
            '/SC',
            'DAILY',
            '/TN',
            taskName,
            '/TR',
            action,
            '/ST',
            schedule.run_at,
            '/F',
            '/IT',
            '/RL',
            'LIMITED',
        ]);
        try {
            await configureMissedRunRecovery(taskName);
        } catch (error) {
            try {
                await runScheduledTasksCommand([
                    '/Delete',
                    '/TN',
                    taskName,
                    '/F',
                ]);
            } catch (rollbackError) {
                throw new AggregateError(
                    [error, rollbackError],
                    'Task Scheduler settings failed and the partial task could not be removed.',
                );
            }
            throw error;
        }
    }

    async removeDaily(scheduleId) {
        if (process.platform !== 'win32') {
            throw new Error('Scheduled report delivery is available on Windows.');
        }
        await runScheduledTasksCommand([
            '/Delete',
            '/TN',
            scheduleTaskName(scheduleId),
            '/F',
        ]);
    }

    async reconcile(schedules, previouslyRegisteredIds = []) {
        if (process.platform !== 'win32') {
            if (schedules.some((schedule) => schedule.enabled)) {
                throw new Error(
                    'Scheduled report delivery is available on Windows.',
                );
            }
            return [];
        }

        const enabledSchedules = schedules.filter((schedule) => schedule.enabled);
        const enabledIds = new Set(
            enabledSchedules.map((schedule) => schedule.schedule_id),
        );
        for (const scheduleId of previouslyRegisteredIds) {
            if (!enabledIds.has(scheduleId)) {
                await this.removeDaily(scheduleId);
            }
        }
        for (const schedule of enabledSchedules) {
            await this.registerDaily(schedule);
        }

        if (enabledSchedules.length > 0) {
            const action = buildAction(
                this.app,
                recoveryApplicationArguments(this.app),
            );
            await runScheduledTasksCommand([
                '/Create',
                '/SC',
                'ONLOGON',
                '/TN',
                RECOVERY_TASK_NAME,
                '/TR',
                action,
                '/F',
                '/IT',
                '/RL',
                'LIMITED',
            ]);
        } else if (previouslyRegisteredIds.length > 0) {
            await runScheduledTasksCommand([
                '/Delete',
                '/TN',
                RECOVERY_TASK_NAME,
                '/F',
            ]);
        }
        return [...enabledIds];
    }
}
