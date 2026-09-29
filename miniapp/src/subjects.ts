export const SUBJECTS = [
  { id: "math", label: "Математика", grades: [1, 2, 3, 4] },
  { id: "algebra", label: "Алгебра", grades: [5, 6, 7, 8, 9, 10, 11] },
  { id: "geometry", label: "Геометрия", grades: [5, 6, 7, 8, 9, 10, 11] },
  { id: "physics", label: "Физика", grades: [5, 6, 7, 8, 9, 10, 11] },
] as const;

export type SubjectId = (typeof SUBJECTS)[number]["id"];

export const ALL_GRADES = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11] as const;

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
