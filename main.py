"""CLI 기반 메모리 Mini Git을 제공한다."""

from __future__ import annotations

import shlex
from collections.abc import Callable
from datetime import datetime


class Commit:
    """커밋 하나의 메타데이터를 보관한다."""

    def __init__(
        self,
        commit_hash: str,
        message: str,
        author: str,
        timestamp: str,
        parents: list[str],
    ) -> None:
        self.hash = commit_hash
        self.message = message
        self.author = author
        self.timestamp = timestamp
        self.parents = parents


class Repository:
    """메모리 안의 커밋과 현재 브랜치 상태를 관리한다."""

    def __init__(self) -> None:
        self.initialized = False
        self.current_user: str | None = None
        self.current_branch: str | None = None
        self.branches: dict[str, str | None] = {}
        self.commits: dict[str, Commit] = {}
        self.keyword_index: dict[str, list[str]] = {}
        self.author_index: dict[str, list[str]] = {}
        self._commit_counter = 0

    def init_repository(self, user_name: str) -> None:
        """저장소를 비우고 main 브랜치와 현재 사용자를 설정한다."""
        self.initialized = True
        self.current_user = user_name
        self.current_branch = "main"
        self.branches = {"main": None}
        self.commits = {}
        self.keyword_index = {}
        self.author_index = {}
        self._commit_counter = 0

    def create_commit(self, message: str) -> Commit:
        """현재 HEAD를 부모로 하는 새 커밋을 만들고 반환한다."""
        self._require_initialized()

        parent_hash = self._current_head()
        parents = [] if parent_hash is None else [parent_hash]
        commit = Commit(
            commit_hash=self._make_hash(),
            message=message,
            author=self.current_user or "",
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            parents=parents,
        )

        self.commits[commit.hash] = commit
        self._add_to_indexes(commit)
        self.branches[self.current_branch or "main"] = commit.hash
        return commit

    def create_branch(self, branch_name: str) -> None:
        """현재 HEAD를 가리키는 새 브랜치를 만든다."""
        self._require_initialized()
        if branch_name in self.branches:
            raise ValueError(f"Branch already exists: {branch_name}")

        self.branches[branch_name] = self._current_head()

    def switch_branch(self, branch_name: str) -> None:
        """현재 작업 브랜치를 존재하는 브랜치로 바꾼다."""
        self._require_initialized()
        if branch_name not in self.branches:
            raise ValueError(f"Unknown branch: {branch_name}")

        self.current_branch = branch_name

    def get_log_commits(self) -> list[Commit]:
        """저장소의 모든 커밋을 부모가 먼저 오도록 반환한다."""
        self._require_initialized()
        result: list[Commit] = []
        visited: set[str] = set()
        for commit_hash in self.commits:
            self._collect_parents_first(commit_hash, visited, result)
        return result

    def get_ancestors(self, commit_hash: str) -> list[Commit]:
        """지정 커밋을 제외한 모든 조상을 중복 없이 반환한다."""
        commit = self._require_commit(commit_hash)
        result: list[Commit] = []
        visited: set[str] = set()

        for parent_hash in commit.parents:
            self._collect_parents_first(parent_hash, visited, result)
        return result

    def get_sorted_log_commits(self, sort_by: str) -> list[Commit]:
        """전체 로그를 지정한 기준으로 직접 구현한 정렬로 반환한다."""
        commits = self.get_log_commits()
        if sort_by == "date":
            return self._insertion_sort(commits, lambda commit: commit.timestamp)
        if sort_by == "author":
            return self._insertion_sort(commits, lambda commit: commit.author)
        raise ValueError(f"Invalid sort option: {sort_by}")

    def find_shortest_path(
        self, start_hash: str, end_hash: str
    ) -> list[str] | None:
        """부모 연결을 무방향으로 보고 BFS 최단 경로를 반환한다."""
        self._require_commit(start_hash)
        self._require_commit(end_hash)

        if start_hash == end_hash:
            return [start_hash]

        queue: list[list[str]] = [[start_hash]]
        visited = {start_hash}
        queue_index = 0

        while queue_index < len(queue):
            path = queue[queue_index]
            queue_index += 1
            current_hash = path[-1]

            for neighbor_hash in self._undirected_neighbors(current_hash):
                if neighbor_hash in visited:
                    continue

                next_path = path + [neighbor_hash]
                if neighbor_hash == end_hash:
                    return next_path

                visited.add(neighbor_hash)
                queue.append(next_path)

        return None

    def search_by_keyword(self, keyword: str) -> list[Commit]:
        """keyword 역색인으로 메시지 토큰과 일치하는 커밋을 반환한다."""
        self._require_initialized()
        hashes = self.keyword_index.get(keyword.lower(), [])
        return [self.commits[commit_hash] for commit_hash in hashes]

    def search_by_author(self, author: str) -> list[Commit]:
        """author 역색인으로 작성자가 일치하는 커밋을 반환한다."""
        self._require_initialized()
        hashes = self.author_index.get(author.lower(), [])
        return [self.commits[commit_hash] for commit_hash in hashes]

    def _require_initialized(self) -> None:
        """초기화 전 저장소 사용을 막는다."""
        if not self.initialized:
            raise ValueError("Repository not initialized")

    def _current_head(self) -> str | None:
        """현재 브랜치가 가리키는 커밋 해시를 반환한다."""
        self._require_initialized()
        if self.current_branch is None:
            raise ValueError("No current branch")
        return self.branches[self.current_branch]

    def _make_hash(self) -> str:
        """세션 내에서 중복되지 않는 재현 가능한 커밋 해시를 만든다."""
        self._commit_counter += 1
        return f"c{self._commit_counter:06d}"

    def _add_to_indexes(self, commit: Commit) -> None:
        """새 커밋의 메시지 토큰과 작성자를 역색인에 등록한다."""
        added_keywords: set[str] = set()
        for keyword in commit.message.lower().split():
            if keyword in added_keywords:
                continue
            self.keyword_index.setdefault(keyword, []).append(commit.hash)
            added_keywords.add(keyword)

        author_key = commit.author.lower()
        self.author_index.setdefault(author_key, []).append(commit.hash)

    def _require_commit(self, commit_hash: str) -> Commit:
        """존재하는 커밋을 반환하고, 없으면 사용자용 오류를 발생시킨다."""
        self._require_initialized()
        if commit_hash not in self.commits:
            raise ValueError(f"Unknown commit: {commit_hash}")
        return self.commits[commit_hash]

    def _collect_parents_first(
        self,
        commit_hash: str,
        visited: set[str],
        result: list[Commit],
    ) -> None:
        """DFS로 부모를 먼저 방문한 뒤 현재 커밋을 결과에 넣는다."""
        if commit_hash in visited:
            return

        visited.add(commit_hash)
        commit = self.commits[commit_hash]
        for parent_hash in commit.parents:
            self._collect_parents_first(parent_hash, visited, result)
        result.append(commit)

    def _undirected_neighbors(self, commit_hash: str) -> list[str]:
        """PATH 탐색용으로 부모와 자식을 모두 이웃으로 반환한다."""
        commit = self.commits[commit_hash]
        neighbors = set(commit.parents)

        for possible_child in self.commits.values():
            if commit_hash in possible_child.parents:
                neighbors.add(possible_child.hash)

        return self._lexicographic_hashes(neighbors)

    @staticmethod
    def _lexicographic_hashes(hashes: set[str]) -> list[str]:
        """금지된 표준 정렬 API 없이 해시를 사전순으로 정렬한다."""
        result: list[str] = []
        for commit_hash in hashes:
            position = 0
            while (
                position < len(result)
                and result[position] < commit_hash
            ):
                position += 1
            result.insert(position, commit_hash)
        return result

    @staticmethod
    def _insertion_sort(
        items: list[Commit], key: Callable[[Commit], str]
    ) -> list[Commit]:
        """삽입 정렬로 key 기준 오름차순 정렬 결과를 새 목록으로 반환한다.

        같은 key일 때 기존 항목 뒤에 삽입하므로 입력 순서가 유지되는 안정 정렬이다.
        """
        result: list[Commit] = []
        for item in items:
            position = len(result)
            while position > 0 and key(result[position - 1]) > key(item):
                position -= 1
            result.insert(position, item)
        return result


class MiniGitCLI:
    """사용자 입력을 파싱하고, 명령을 저장소 기능으로 분배하는 CLI다."""

    EXIT_COMMANDS = {"EXIT", "QUIT"}
    KNOWN_COMMANDS = {
        "INIT",
        "BRANCH",
        "SWITCH",
        "COMMIT",
        "LOG",
        "PATH",
        "ANCESTORS",
        "SEARCH",
    }

    def __init__(self) -> None:
        self.repository = Repository()

    def parse_line(self, line: str) -> tuple[str, list[str]] | None:
        """입력 한 줄을 대문자 명령어와 인자 목록으로 나눈다.

        빈 줄은 None을 반환한다. shlex.split()을 사용하므로 따옴표 안의
        공백은 하나의 인자로 유지된다. 닫히지 않은 따옴표는 ValueError가 된다.
        """
        if not line.strip():
            return None

        parts = shlex.split(line)
        command = parts[0].upper()
        args = parts[1:]
        return command, args

    def handle_command(self, command: str, args: list[str]) -> str:
        """명령에 맞는 핸들러를 호출하고 사용자용 결과를 반환한다."""
        if command == "INIT":
            return self.handle_init(args)
        if command == "COMMIT":
            return self.handle_commit(args)
        if command == "BRANCH":
            return self.handle_branch(args)
        if command == "SWITCH":
            return self.handle_switch(args)
        if command == "LOG":
            return self.handle_log(args)
        if command == "ANCESTORS":
            return self.handle_ancestors(args)
        if command == "PATH":
            return self.handle_path(args)
        if command == "SEARCH":
            return self.handle_search(args)
        if command in self.KNOWN_COMMANDS:
            return f"{command} is not implemented yet."

        return f"Unknown command: {command}"

    def handle_init(self, args: list[str]) -> str:
        """INIT 인자를 검증하고 저장소 초기화를 요청한다."""
        if len(args) != 1:
            return "Invalid args"

        user_name = args[0]
        self.repository.init_repository(user_name)
        return (
            "Initialized repository.\n"
            "Current branch: main\n"
            f"Current user: {user_name}"
        )

    def handle_commit(self, args: list[str]) -> str:
        """COMMIT 인자를 검증하고 새 커밋의 결과를 반환한다."""
        if len(args) != 1:
            return "Invalid args"

        try:
            commit = self.repository.create_commit(args[0])
        except ValueError as error:
            return str(error)

        branch = self.repository.current_branch
        return f"[{branch} {commit.hash}] {commit.message}"

    def handle_branch(self, args: list[str]) -> str:
        """BRANCH 인자를 검증하고 새 브랜치 생성을 요청한다."""
        if len(args) != 1:
            return "Invalid args"

        branch_name = args[0]
        try:
            self.repository.create_branch(branch_name)
        except ValueError as error:
            return str(error)

        return f"Created branch: {branch_name}"

    def handle_switch(self, args: list[str]) -> str:
        """SWITCH 인자를 검증하고 현재 브랜치 전환을 요청한다."""
        if len(args) != 1:
            return "Invalid args"

        branch_name = args[0]
        try:
            self.repository.switch_branch(branch_name)
        except ValueError as error:
            return str(error)

        return f"Switched to branch: {branch_name}"

    def handle_log(self, args: list[str]) -> str:
        """기본 LOG 또는 정렬 옵션 LOG를 출력 형식으로 바꾼다."""
        if len(args) > 1:
            return "Invalid args"

        try:
            if not args:
                commits = self.repository.get_log_commits()
            elif args[0].startswith("--sort-by="):
                sort_by = args[0].removeprefix("--sort-by=")
                if not sort_by:
                    return "Invalid args"
                commits = self.repository.get_sorted_log_commits(sort_by)
            else:
                return "Invalid args"
        except ValueError as error:
            if str(error).startswith("Invalid sort option:"):
                return "Invalid args"
            return str(error)

        if not commits:
            return "No commits"
        return "\n".join(self._format_commit(commit) for commit in commits)

    def handle_ancestors(self, args: list[str]) -> str:
        """ANCESTORS 인자를 검증하고 모든 조상을 출력 형식으로 바꾼다."""
        if len(args) != 1:
            return "Invalid args"

        try:
            commits = self.repository.get_ancestors(args[0])
        except ValueError as error:
            return str(error)

        if not commits:
            return "No ancestors"
        return "\n".join(self._format_commit(commit) for commit in commits)

    def handle_path(self, args: list[str]) -> str:
        """PATH 인자를 검증하고 최단 경로를 출력 형식으로 바꾼다."""
        if len(args) != 2:
            return "Invalid args"

        try:
            path = self.repository.find_shortest_path(args[0], args[1])
        except ValueError as error:
            return str(error)

        if path is None:
            return "No path"
        return f"Path: {' -> '.join(path)}"

    def handle_search(self, args: list[str]) -> str:
        """SEARCH 키워드 또는 --author 옵션을 역색인 검색으로 처리한다."""
        if len(args) != 1:
            return "Invalid args"

        query = args[0]
        try:
            if query.startswith("--author="):
                author = query.removeprefix("--author=")
                if not author:
                    return "Invalid args"
                commits = self.repository.search_by_author(author)
            elif query.startswith("--"):
                return "Invalid args"
            else:
                commits = self.repository.search_by_keyword(query)
        except ValueError as error:
            return str(error)

        count = len(commits)
        label = "commit" if count == 1 else "commits"
        lines = [f"Found {count} {label}:"]
        lines.extend(f"- {commit.hash}: {commit.message}" for commit in commits)
        return "\n".join(lines)

    @staticmethod
    def _format_commit(commit: Commit) -> str:
        """커밋의 필수 식별 정보를 사람이 읽을 수 있게 표현한다."""
        return (
            f"commit {commit.hash} ({commit.author}, {commit.timestamp})\n"
            f"{commit.message}"
        )

    def run(self) -> None:
        """입력 → 파싱 → 명령 분배 → 출력을 반복한다."""
        while True:
            try:
                line = input("mini-git> ")
            except EOFError:
                print()
                break

            try:
                parsed = self.parse_line(line)
            except ValueError:
                print("Invalid args")
                continue

            if parsed is None:
                continue

            command, args = parsed
            if command in self.EXIT_COMMANDS:
                break

            print(self.handle_command(command, args))


def main() -> None:
    """Mini Git CLI를 시작한다."""
    MiniGitCLI().run()


if __name__ == "__main__":
    main()
