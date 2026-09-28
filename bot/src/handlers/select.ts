import type { Context } from "@maxhub/max-bot-api";
import { listStudents, listWorks, setState } from "../api.js";
import { kb, openMiniappButton } from "../max.js";

function chunk<T>(items: T[], size: number): T[][] {
  const rows: T[][] = [];
  for (let i = 0; i < items.length; i += size) rows.push(items.slice(i, i + size));
  return rows;
}

export async function handleSelectWork(ctx: Context): Promise<void> {
  const userId = ctx.message?.sender?.user_id ?? ctx.user?.user_id;
  if (!userId) return;

  try {
    const works = await listWorks(String(userId));
    if (works.length === 0) {
      await ctx.reply(
        "У тебя пока нет работ. Создай первую в мини-приложении.",
        {
          attachments: [
            kb.inlineKeyboard([[openMiniappButton("Открыть", "works/new")]]),
          ],
        }
      );
      return;
    }

    const buttons = works
      .slice(0, 20)
      .map((w) => kb.button.callback(w.title, `work:${w.id}`));
    await ctx.reply("Выбери работу:", {
      attachments: [kb.inlineKeyboard(chunk(buttons, 1))],
    });
  } catch {
    await ctx.reply("Не удалось получить список работ. Попробуй позже.");
  }
}

export async function handleSelectStudent(ctx: Context): Promise<void> {
  const userId = ctx.message?.sender?.user_id ?? ctx.user?.user_id;
  if (!userId) return;

  try {
    const students = await listStudents(String(userId));
    if (students.length === 0) {
      await ctx.reply(
        "У тебя пока нет учеников. Добавь в мини-приложении.",
        {
          attachments: [
            kb.inlineKeyboard([[openMiniappButton("Открыть", "students/new")]]),
          ],
        }
      );
      return;
    }

    const buttons = students
      .slice(0, 30)
      .map((s) =>
        kb.button.callback(`${s.display_name} · ${s.class_id}`, `student:${s.id}`)
      );
    await ctx.reply("Выбери ученика:", {
      attachments: [kb.inlineKeyboard(chunk(buttons, 1))],
    });
  } catch {
    await ctx.reply("Не удалось получить список учеников. Попробуй позже.");
  }
}

export async function handleWorkPicked(ctx: Context): Promise<void> {
  const userId = ctx.user?.user_id ?? ctx.message?.sender?.user_id;
  const workId = ctx.match?.[1];
  if (!userId || !workId) return;
  try {
    await setState(String(userId), { current_work_id: workId });
    await ctx.answerOnCallback({
      message: { text: "Работа выбрана. Теперь выбери ученика: /student", attachments: [] },
    });
  } catch {
    await ctx.answerOnCallback({
      message: { text: "Не удалось сохранить выбор", attachments: [] },
    });
  }
}

export async function handleStudentPicked(ctx: Context): Promise<void> {
  const userId = ctx.user?.user_id ?? ctx.message?.sender?.user_id;
  const studentId = ctx.match?.[1];
  if (!userId || !studentId) return;
  try {
    await setState(String(userId), { current_student_id: studentId });
    await ctx.answerOnCallback({
      message: {
        text: "Ученик выбран. Присылай фото работы.",
        attachments: [],
      },
    });
  } catch {
    await ctx.answerOnCallback({
      message: { text: "Не удалось сохранить выбор", attachments: [] },
    });
  }
}
