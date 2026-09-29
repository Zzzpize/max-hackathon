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
