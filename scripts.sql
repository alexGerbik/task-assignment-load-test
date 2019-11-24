select  * from task order by created_at;
select count(*) from task where created_at < '2019-11-22 16:25:00.504211';

-- 3000 should
--  -88 missing
-- 2912 actual
-- -287 wrong
-- 2625
-- +375 actual missing

select count(*), original_tasks.id notnull as task_exists, completed_task.task_id notnull as task_completed
from
    (select * from task t where t.created_at < '2019-11-22 16:25:00.504211') as original_tasks
full outer join completed_task on original_tasks.id = completed_task.task_id
group by task_exists, task_completed
;

-- initial but not completed
create or replace view not_completed_normal as
select original_tasks.id
from
    (select * from task t where t.created_at < '2019-11-22 16:25:00.504211') as original_tasks
full outer join completed_task on original_tasks.id = completed_task.task_id
where original_tasks.id notnull and completed_task.task_id isnull
;

select * from task
    where type = 'QA'
    and (type_specific_data ->> 'inspected_task_id')::uuid in (select * from not_completed_normal)
;

select *
from task
where id in (select * from not_completed_normal)
;


select count(*) from completed_task;
-- 3000

select count(type), type, is_pushback
from task
group by type, is_pushback
order by is_pushback
;
-- count	type	is_pusback
-- ---------------------------
-- 1258		CC		false
-- 772		QC		false
-- 3000		NORMAL	false
-- 4006		QA		false
-- 2120		NORMAL	true
-- 2120		QA		true

-- QC probability = 0.15
-- CC probability = 0.25
-- 772 / (772 + 1258 + 3000) = 0.15347912524850896
-- 1258 / (772 + 1258 + 3000) = 0.25009940357852883


select type, count(counts.times_assigned), counts.times_assigned
from task
join (
    select count(*) as times_assigned, task_id
    from assignment
    where status = 'FINISHED'
    group by task_id
) as counts on task.id = counts.task_id
group by type, counts.times_assigned
;
-- type		count	times_assigned
-- ------------------
-- QC		 772	1
-- CC		1258	1
-- QA		6126	1
-- NORMAL	5120	1

select count(type), type, is_pushback
from task
join assignment a on task.id = a.task_id
group by type, is_pushback
order by is_pushback
;





select name, config from task_set;

select task_id, output_data from completed_task;

select u.name,
       ts.name                 as app_name,
       s.normal_tasks_finished as tasks_finished,
       total_time_spent        as time_spent,
       check_type,
       total_successful,
       total_failed
from statistics s
         join "user" u on s.user_id = u.id
         join task_set ts on s.task_set_id = ts.id;

{"class": "B", "nodules": [{"x": 12, "y": 17, "dx": 10, "dy": 10}, {"x": 150, "y": 200, "dx": 10, "dy": 10}], "difficulty": "hard"}




explain analyse
SELECT *
FROM task
         JOIN task_set ON task_set.id = task.task_set_id
         JOIN "group" ON task_set.id = "group".task_set_id
         JOIN user_group AS user_group_1 ON "group".id = user_group_1.group_id
         JOIN "user" ON "user".id = user_group_1.user_id
         LEFT OUTER JOIN exclusion ON exclusion.task_id = task.id AND exclusion.user_id = "user".id
         LEFT OUTER JOIN (SELECT assignment_1.task_id                        AS task_id,
                                 count(assignment_1.task_id)                 AS assignments_count,
                                 bool_or(assignment_1.user_id != '364ff133-e4a7-4d09-a7c9-98b8ea32bdf8') AS started_by_anyone,
                                 bool_or(assignment_1.user_id = '364ff133-e4a7-4d09-a7c9-98b8ea32bdf8')  AS previously_assigned
                          FROM assignment AS assignment_1
                          WHERE coalesce(assignment_1.deadline, 'infinity'::timestamp) >= current_timestamp
                          GROUP BY assignment_1.task_id) AS anon_2 ON task.id = anon_2.task_id
WHERE "user".id = '364ff133-e4a7-4d09-a7c9-98b8ea32bdf8'
  AND task.status = 'PROC'
  AND exclusion.user_id IS NULL
  AND (task.assigned_group_id IS NULL OR task.assigned_group_id = "group".id)
  AND NOT coalesce(anon_2.previously_assigned, FALSE)
  AND coalesce(anon_2.assignments_count, 0) < task.assignments_required
ORDER BY task.priority DESC
LIMIT 5
FOR UPDATE OF task SKIP LOCKED;

explain analyse SELECT task_set.allow_skip AND task.type != 'CC' AND NOT task.is_pushback AND
       (task.assigned_group_id IS NULL OR task.assigned_group_id = task_set.default_group_id OR
        NOT coalesce(anon_2.started_by_anyone, False)) AS anon_1,
       task.created_at                              AS task_created_at,
       task.updated_at                              AS task_updated_at,
       task.id                                      AS task_id,
       task.task_set_id                             AS task_task_set_id,
       task.input_data                              AS task_input_data,
       task.priority                                AS task_priority,
       task.assigned_group_id                       AS task_assigned_group_id,
       task.assignments_required                    AS task_assignments_required,
       task.type                                    AS task_type,
       task.status                                  AS task_status,
       task.type_specific_data                      AS task_type_specific_data,
       task.is_pushback                             AS task_is_pushback
FROM task
         JOIN task_set ON task_set.id = task.task_set_id
         JOIN "group" ON task_set.id = "group".task_set_id
         JOIN user_group AS user_group_1 ON "group".id = user_group_1.group_id
         JOIN "user" ON "user".id = user_group_1.user_id
         LEFT OUTER JOIN exclusion ON exclusion.task_id = task.id AND exclusion.user_id = "user".id
         LEFT OUTER JOIN (SELECT assignment_1.task_id                      AS task_id,
                                 count(assignment_1.task_id)               AS assignments_count,
                                 bool_or(assignment_1.user_id != '364ff133-e4a7-4d09-a7c9-98b8ea32bdf8'::uuid) AS started_by_anyone,
                                 bool_or(assignment_1.user_id = '364ff133-e4a7-4d09-a7c9-98b8ea32bdf8'::uuid)  AS previously_assigned
                          FROM assignment AS assignment_1
                          WHERE assignment_1.deadline IS NULL
                             OR assignment_1.deadline >= current_timestamp
                          GROUP BY assignment_1.task_id) AS anon_2 ON task.id = anon_2.task_id
WHERE "user".id = '364ff133-e4a7-4d09-a7c9-98b8ea32bdf8'::uuid
  AND task.status = 'PROC'
  AND exclusion.user_id IS NULL
  AND (task.assigned_group_id IS NULL OR task.assigned_group_id = "group".id)
  AND NOT coalesce(anon_2.previously_assigned, False)
  AND coalesce(anon_2.assignments_count, 0) < task.assignments_required
ORDER BY task.priority DESC
LIMIT 5



select count(*), type, (
    Select count(*) from assignment where assignment.task_id = task.id
    ) as c
from task
         join assignment a on task.id = a.task_id
group by type, c
;


SELECT task_set.allow_skip AND task.type != :type_1 AND NOT task.is_pushback AND
       (task.assigned_group_id IS NULL OR task.assigned_group_id = task_set.default_group_id OR
        NOT coalesce(anon_2.started_by_anyone, :coalesce_1)) AS anon_1,
       task.created_at                                       AS task_created_at,
       task.updated_at                                       AS task_updated_at,
       task.id                                               AS task_id,
       task.task_set_id                                      AS task_task_set_id,
       task.input_data                                       AS task_input_data,
       task.priority                                         AS task_priority,
       task.assigned_group_id                                AS task_assigned_group_id,
       task.assignments_required                             AS task_assignments_required,
       task.type                                             AS task_type,
       task.status                                           AS task_status,
       task.type_specific_data                               AS task_type_specific_data,
       task.is_pushback                                      AS task_is_pushback
FROM task
         JOIN task_set ON task_set.id = task.task_set_id
         JOIN "group" ON task_set.id = "group".task_set_id
         JOIN user_group AS user_group_1 ON "group".id = user_group_1.group_id
         JOIN "user" ON "user".id = user_group_1.user_id
         LEFT OUTER JOIN exclusion ON exclusion.task_id = task.id AND exclusion.user_id = "user".id
         LEFT OUTER JOIN (SELECT assignment_1.task_id                        AS task_id,
                                 count(assignment_1.task_id)                 AS assignments_count,
                                 bool_or(assignment_1.user_id != :user_id_1) AS started_by_anyone,
                                 bool_or(assignment_1.user_id = :user_id_2)  AS previously_assigned
                          FROM assignment AS assignment_1
                          WHERE assignment_1.deadline IS NULL
                             OR assignment_1.deadline >= :deadline_1
                          GROUP BY assignment_1.task_id) AS anon_2 ON task.id = anon_2.task_id
WHERE "user".id = :id_1
  AND task.status = :status_1
  AND exclusion.user_id IS NULL
  AND (task.assigned_group_id IS NULL OR task.assigned_group_id = "group".id)
  AND NOT coalesce(anon_2.previously_assigned, :coalesce_2)
  AND coalesce(anon_2.assignments_count, :coalesce_3) < task.assignments_required
ORDER BY task.priority DESC
LIMIT :param_1
FOR UPDATE OF task SKIP LOCKED;





explain analyse SELECT assignment_1.task_id                                                    AS task_id,
       count(assignment_1.task_id)                                             AS assignments_count,
       bool_or(assignment_1.user_id != '364ff133-e4a7-4d09-a7c9-98b8ea32bdf8') AS started_by_anyone,
       bool_or(assignment_1.user_id = '364ff133-e4a7-4d09-a7c9-98b8ea32bdf8')  AS previously_assigned
FROM assignment AS assignment_1
WHERE
      coalesce(assignment_1.deadline, 'infinity'::timestamp) >= current_timestamp
GROUP BY assignment_1.task_id
;


explain analyse SELECT *
FROM assignment AS assignment_1
WHERE
      coalesce(assignment_1.deadline, 'infinity'::timestamp) >= current_timestamp
;




create table if not exists assignment
(
	created_at timestamp not null,
	updated_at timestamp not null,
	task_id uuid not null
		constraint assignment_task_id_fkey
			references task
				on delete cascade,
	user_id uuid not null
		constraint assignment_user_id_fkey
			references "user"
				on delete cascade,
	time_spent interval not null,
	deadline timestamp,
	status _assignmentstatus not null,
	result jsonb not null,
	extra_data jsonb not null,
	constraint assignment_pkey
		primary key (task_id, user_id)
);

alter table assignment owner to postgres;

create index if not exists assignment_idx_current
	on assignment (deadline, user_id);

create index if not exists assignment_task_id_deadline_index
	on assignment (task_id, deadline);

create trigger remove_outdated_assignments
	before insert
	on assignment
	for each row
	execute procedure remove_outdated_assignments();




CREATE INDEX stats_idx ON statistics (task_set_id, user_id, check_type);

CREATE INDEX ccs_idx ON consistency_check_schedule (triggered, user_id, trigger_time) WHERE triggered = False;

create INDEX user_group_idx ON user_group (user_id, group_id);

create index user_token_idx on "user" (token);

create INDEX exclusion_idx ON exclusion (task_id, user_id);

create INDEX task_idx ON task (status, assigned_group_id, priority)
where status='PROC';

create INDEX assignment_idx on assignment (deadline, task_id);

create INDEX assignment_idx_current on assignment (deadline, user_id);


create INDEX assignment_idx on assignment (task_id, (deadline IS NULL), deadline);
create INDEX assignment_idx on assignment (task_id, coalesce(deadline, 'infinity'::timestamp));

create INDEX assignment_idx on assignment (coalesce(deadline, 'infinity'::timestamp));

create INDEX assignment_idx on assignment (task_id, coalesce(deadline, 'infinity'::timestamp));

create INDEX assignment_idx on assignment (coalesce(deadline, 'infinity'::timestamp), task_id);

drop INDEX assignment_idx;







Violation:
	max_assignments > 1 or has CC/QC and not merging algorithm


Low priority:
	Mypy
	pipenv lock
	database consistency check for Assignment.deadline and Assignment.status.PROC
	use context in pipeline and pass context to hooks

WTF?:
	is_qa task set attribute?
	task -> qa -> task

To be tested:
	normal task finish unit-tests
	qa task unit-tests
	qa integration tests


Useful but not needed right now (needed when migrate):
	CORS Flask-Cors==3.0.7
	Convenience method for taskset/tasks creation with validation
	Validate submitted/saved data
	QA tasks deadline? (if there several QA - recycle, if one - no need, might lose saved result)
	dQA rQA
	single file contains all the configuration

Bugs:
	TaskSetId in request!!!!
	CC annotations uuid are not unique in QA task
	when assignment is outdated and user gets assigned to the same task -> integrity error


Double-Checked Locking
deadline +infinity timestamp

Preformance testing:
		indices
	RabbitMQ

separate QAS TAS services/ yes/no
log sqls: yes/no
indices: yes/no

28/29 thanksgiving

--------------------
recycle? (self.wait)
skip?
not final save?
--------------------

QC/CC QC/CC with given probabilities!
multi-readers - above min and below max!
validate all data is correctly saved!


single-reader
multiple-reader n = 3
multiple-reader with adaptive logic
multiple-reader with adaptive logic and task amount = 4
