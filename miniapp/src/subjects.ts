// Продукт нацелен на младшие классы: математика, 1–4. Расширение на другие
// предметы и старшие классы намеренно закрыто — размывает УТП «фундамент
// для мелких», подмывает питч презентации.
export const SUBJECTS = [
  { id: "math", label: "Математика", grades: [1, 2, 3, 4] },
] as const;

export type SubjectId = (typeof SUBJECTS)[number]["id"];

export const ALL_GRADES = [1, 2, 3, 4] as const;

export function subjectsForGrade(grade: number): typeof SUBJECTS[number][] {
  return SUBJECTS.filter((s) => s.grades.includes(grade as never));
}

export function gradesForSubject(subject: SubjectId): number[] {
  const found = SUBJECTS.find((s) => s.id === subject);
  return found ? [...found.grades] : [];
}

export function subjectLabel(id: string): string {
  return SUBJECTS.find((s) => s.id === id)?.label ?? id;
}

export function subjectOptionLabel(subject: typeof SUBJECTS[number]): string {
  const gs = subject.grades;
  const range = gs[0] === gs[gs.length - 1] ? `${gs[0]}` : `${gs[0]}–${gs[gs.length - 1]}`;
  return `${subject.label} (${range} кл.)`;
}

/** Ближайший допустимый для предмета класс. Если текущий подходит — вернёт его. */
export function nearestGradeFor(subject: SubjectId, current: number): number {
  const grades = gradesForSubject(subject);
  if (grades.includes(current)) return current;
  return grades.reduce(
    (best, g) => (Math.abs(g - current) < Math.abs(best - current) ? g : best),
    grades[0]
  );
}

/** Первый предмет, поддерживающий класс. Если такого нет — вернёт math. */
export function firstSubjectFor(grade: number): SubjectId {
  return subjectsForGrade(grade)[0]?.id ?? "math";
}
