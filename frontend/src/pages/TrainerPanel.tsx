import React, { useEffect, useState } from 'react';
import { api } from '../services/api';
import { useAuth } from '../context/AuthContext';
import { Member } from '../types/member';
import { Trainer, TrainerAvailability, TrainingSession } from '../types/ops';
import {
  Activity,
  AlertTriangle,
  Calendar,
  CheckCircle,
  Clock,
  Phone,
  RefreshCw,
} from 'lucide-react';

const isoDate = (date: Date) => date.toISOString().slice(0, 10);
const todayIso = () => isoDate(new Date());
const WEEKDAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];

const inputClass = 'px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white';

export const TrainerPanel: React.FC = () => {
  const { user, roles } = useAuth();
  const isManager = roles.some((role) => role === 'owner' || role === 'admin' || role === 'reception');

  const [trainers, setTrainers] = useState<Trainer[]>([]);
  const [members, setMembers] = useState<Member[]>([]);
  const [selectedTrainerId, setSelectedTrainerId] = useState<number | null>(null);
  const [sessions, setSessions] = useState<TrainingSession[]>([]);
  const [availability, setAvailability] = useState<TrainerAvailability[]>([]);
  const [assignedIds, setAssignedIds] = useState<number[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [slot, setSlot] = useState({ weekday: '0', start_time: '06:00', end_time: '10:00' });
  const [booking, setBooking] = useState({ member_id: '', start: '06:00', end: '07:00' });

  const loadBase = async () => {
    setLoading(true);
    try {
      const [trainerList, memberList] = await Promise.all([api.getTrainers(), api.getMembers()]);
      setTrainers(trainerList);
      setMembers(memberList);
      const mine = trainerList.find((trainer) => trainer.user_id === user?.id);
      setSelectedTrainerId(mine?.id ?? trainerList[0]?.id ?? null);
      setError(null);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  };

  const loadTrainerData = async (trainerId: number) => {
    try {
      const [sessionList, slotList, assignments] = await Promise.all([
        api.getSessions({ trainer_id: trainerId, on_date: todayIso() }),
        api.getTrainerAvailability(trainerId),
        api.getTrainerMembers(trainerId),
      ]);
      setSessions(sessionList);
      setAvailability(slotList);
      setAssignedIds(assignments.map((assignment) => assignment.member_id));
      setError(null);
    } catch (err) {
      setError((err as Error).message);
    }
  };

  useEffect(() => {
    loadBase();
  }, [user?.id]);

  useEffect(() => {
    if (selectedTrainerId) loadTrainerData(selectedTrainerId);
  }, [selectedTrainerId]);

  const run = async (action: () => Promise<unknown>) => {
    try {
      await action();
      if (selectedTrainerId) await loadTrainerData(selectedTrainerId);
    } catch (err) {
      setError((err as Error).message);
    }
  };

  const markAttendance = (session: TrainingSession) =>
    run(() => api.recordTrainerAttendance(session.id, { checked_in_at: new Date().toISOString() }));

  const selectedTrainer = trainers.find((trainer) => trainer.id === selectedTrainerId);
  const assignedMembers = members.filter((member) => assignedIds.includes(member.id));
  const bookedMemberIds = new Set(sessions.map((session) => session.member_id));

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight flex items-center space-x-2">
            <Activity className="w-7 h-7 text-emerald-600" />
            <span>Trainer Hub</span>
          </h1>
          <p className="text-sm text-slate-500">
            {selectedTrainer ? `${selectedTrainer.full_name} · ${selectedTrainer.specialty || 'General'}` : 'Assigned members, availability and sessions'}
          </p>
        </div>
        <div className="flex items-center gap-2 self-start">
          {isManager && trainers.length > 0 && (
            <select
              value={selectedTrainerId ?? ''}
              onChange={(e) => setSelectedTrainerId(Number(e.target.value))}
              className={inputClass}
              aria-label="Select trainer"
            >
              {trainers.map((trainer) => (
                <option key={trainer.id} value={trainer.id}>{trainer.full_name}</option>
              ))}
            </select>
          )}
          <button
            onClick={() => {
              loadBase();
              if (selectedTrainerId) loadTrainerData(selectedTrainerId);
            }}
            className="p-2 text-slate-500 hover:text-slate-800 hover:bg-slate-100 rounded-lg"
            title="Refresh"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {error && (
        <div className="p-4 bg-rose-50 border border-rose-200 rounded-xl text-rose-700 text-sm flex items-center space-x-2">
          <AlertTriangle className="w-5 h-5 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {loading ? (
        <div className="text-sm text-slate-400">Loading…</div>
      ) : !selectedTrainer ? (
        <div className="bg-white border border-slate-200 rounded-xl p-10 text-center text-sm text-slate-500">
          No trainer profile linked to this login. Ask an owner/admin to create a trainer record and link your user.
        </div>
      ) : (
        <>
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
            <div className="lg:col-span-2 bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
              <div className="p-4 border-b border-slate-200 bg-slate-50 flex items-center justify-between">
                <h2 className="font-semibold text-slate-800 flex items-center gap-2">
                  <Calendar className="w-4 h-4 text-emerald-600" /> Today's sessions
                </h2>
                <span className="text-xs text-slate-500">{sessions.length} booked</span>
              </div>
              {sessions.length === 0 ? (
                <p className="p-8 text-center text-sm text-slate-400">No sessions scheduled for today.</p>
              ) : (
                <ul className="divide-y divide-slate-100">
                  {sessions.map((session) => (
                    <li key={session.id} className="p-4 flex items-center justify-between gap-3">
                      <div>
                        <div className="font-medium text-slate-900">
                          {members.find((member) => member.id === session.member_id)?.full_name || `Member #${session.member_id}`}
                        </div>
                        <div className="text-xs text-slate-500">
                          {session.start_at.slice(11, 16)}–{session.end_at.slice(11, 16)} · {session.status}
                        </div>
                      </div>
                      {session.status === 'scheduled' && (
                        <button
                          onClick={() => markAttendance(session)}
                          className="flex items-center gap-1 px-3 py-1.5 bg-emerald-600 text-white rounded-lg text-xs font-semibold hover:bg-emerald-500"
                        >
                          <CheckCircle className="w-3.5 h-3.5" /> Check in
                        </button>
                      )}
                    </li>
                  ))}
                </ul>
              )}
            </div>

            <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-4">
              <h2 className="font-semibold text-slate-800 mb-3 flex items-center gap-2">
                <Clock className="w-4 h-4 text-emerald-600" /> Weekly availability
              </h2>
              {availability.length === 0 ? (
                <p className="text-sm text-slate-400">No availability slots set.</p>
              ) : (
                <ul className="space-y-1.5 text-sm">
                  {availability.map((item) => (
                    <li key={item.id} className="flex justify-between text-slate-700">
                      <span>{WEEKDAYS[item.weekday]}</span>
                      <span className="text-xs text-slate-500">{item.start_time}–{item.end_time}</span>
                    </li>
                  ))}
                </ul>
              )}
              {isManager && (
                <form
                  onSubmit={(e) => {
                    e.preventDefault();
                    run(() =>
                      api.addTrainerAvailability(selectedTrainer.id, {
                        weekday: Number(slot.weekday),
                        start_time: slot.start_time,
                        end_time: slot.end_time,
                      }),
                    );
                  }}
                  className="mt-4 grid grid-cols-2 gap-2"
                >
                  <select value={slot.weekday} onChange={(e) => setSlot({ ...slot, weekday: e.target.value })} className={inputClass}>
                    {WEEKDAYS.map((day, index) => (
                      <option key={day} value={index}>{day.slice(0, 3)}</option>
                    ))}
                  </select>
                  <button type="submit" className="px-2 py-2 bg-slate-800 text-white rounded-lg text-xs font-semibold">Add slot</button>
                  <input type="time" value={slot.start_time} onChange={(e) => setSlot({ ...slot, start_time: e.target.value })} className={inputClass} />
                  <input type="time" value={slot.end_time} onChange={(e) => setSlot({ ...slot, end_time: e.target.value })} className={inputClass} />
                </form>
              )}
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
            <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-4">
              <h2 className="font-semibold text-slate-800 mb-3">Assigned members ({assignedMembers.length})</h2>
              {assignedMembers.length === 0 ? (
                <p className="text-sm text-slate-400">No members assigned.</p>
              ) : (
                <ul className="divide-y divide-slate-100 text-sm">
                  {assignedMembers.map((member) => (
                    <li key={member.id} className="py-2 flex items-center justify-between gap-2">
                      <div>
                        <div className="font-medium text-slate-900">{member.full_name}</div>
                        {member.health_notes && <div className="text-xs text-amber-700">Health: {member.health_notes}</div>}
                      </div>
                      <a href={`tel:${member.phone}`} className="text-xs text-slate-500 flex items-center gap-1">
                        <Phone className="w-3 h-3" /> {member.phone}
                      </a>
                    </li>
                  ))}
                </ul>
              )}
            </div>

            {isManager && (
              <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-4">
                <h2 className="font-semibold text-slate-800 mb-3">Book a session today</h2>
                <form
                  onSubmit={(e) => {
                    e.preventDefault();
                    const date = todayIso();
                    run(() =>
                      api.createSession({
                        trainer_id: selectedTrainer.id,
                        member_id: Number(booking.member_id),
                        start_at: `${date}T${booking.start}:00`,
                        end_at: `${date}T${booking.end}:00`,
                      }),
                    );
                  }}
                  className="grid grid-cols-2 gap-2"
                >
                  <select required value={booking.member_id} onChange={(e) => setBooking({ ...booking, member_id: e.target.value })} className={`${inputClass} col-span-2`}>
                    <option value="">Member…</option>
                    {assignedMembers.map((member) => (
                      <option key={member.id} value={member.id} disabled={bookedMemberIds.has(member.id)}>
                        {member.full_name}{bookedMemberIds.has(member.id) ? ' (booked)' : ''}
                      </option>
                    ))}
                  </select>
                  <input type="time" required value={booking.start} onChange={(e) => setBooking({ ...booking, start: e.target.value })} className={inputClass} />
                  <input type="time" required value={booking.end} onChange={(e) => setBooking({ ...booking, end: e.target.value })} className={inputClass} />
                  <button type="submit" className="col-span-2 px-3 py-2 bg-emerald-600 text-white rounded-lg text-sm font-semibold">
                    Book session
                  </button>
                </form>
                <p className="text-[11px] text-slate-400 mt-2">
                  Bookings are validated against the trainer's weekly availability.
                </p>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
};
