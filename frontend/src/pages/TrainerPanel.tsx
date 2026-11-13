import React, { useState, useEffect } from 'react';
import { api } from '../services/api';
import { Member } from '../types/member';
import {
  Activity,
  Calendar,
  CheckCircle,
  Clock,
  Phone,
  AlertTriangle,
  HeartPulse,
} from 'lucide-react';

export const TrainerPanel: React.FC = () => {
  const [members, setMembers] = useState<Member[]>([]);
  const [loading, setLoading] = useState(true);
  const [attendanceMarked, setAttendanceMarked] = useState(false);

  // Mock sessions for MVP
  const [sessions, setSessions] = useState([
    { id: 1, time: '06:30 AM', memberName: 'Rahul Sharma', focus: 'Strength & Deadlifts', completed: true },
    { id: 2, time: '08:00 AM', memberName: 'Amit Patel', focus: 'HIIT & Mobility', completed: false },
    { id: 3, time: '05:30 PM', memberName: 'Priya Nair', focus: 'Functional Core', completed: false },
  ]);

  useEffect(() => {
    const fetchAssigned = async () => {
      setLoading(true);
      try {
        const data = await api.getMembers();
        setMembers(data);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    };
    fetchAssigned();
  }, []);

  const toggleSession = (id: number) => {
    setSessions(
      sessions.map((s) => (s.id === id ? { ...s, completed: !s.completed } : s))
    );
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight flex items-center space-x-2">
            <Activity className="w-7 h-7 text-emerald-600" />
            <span>Trainer Hub</span>
          </h1>
          <p className="text-sm text-slate-500">
            Assigned gym members, medical/health precautions, and daily session tracker
          </p>
        </div>

        {/* Quick Check-in Button */}
        <div>
          <button
            onClick={() => setAttendanceMarked(!attendanceMarked)}
            className={`px-4 py-2 rounded-lg text-sm font-semibold flex items-center space-x-2 shadow-sm transition ${
              attendanceMarked
                ? 'bg-emerald-100 text-emerald-800 border border-emerald-300'
                : 'bg-emerald-600 text-white hover:bg-emerald-500'
            }`}
          >
            <CheckCircle className="w-4 h-4" />
            <span>{attendanceMarked ? 'Trainer Checked In' : 'Mark Daily Check-in'}</span>
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left 2 Cols: Assigned Members Roster with Health Flags */}
        <div className="lg:col-span-2 bg-white rounded-2xl border border-slate-200 shadow-sm p-6 space-y-4">
          <div className="flex justify-between items-center">
            <h3 className="font-bold text-slate-900 text-sm flex items-center space-x-2">
              <HeartPulse className="w-4 h-4 text-rose-500" />
              <span>Assigned Members & Health Profiles</span>
            </h3>
            <span className="text-xs text-slate-400 font-medium">{members.length} Members</span>
          </div>

          <div className="space-y-3">
            {loading ? (
              <p className="text-center py-8 text-xs text-slate-400">Loading members...</p>
            ) : members.length === 0 ? (
              <p className="text-center py-8 text-xs text-slate-400">No members assigned yet.</p>
            ) : (
              members.map((member) => (
                <div
                  key={member.id}
                  className="p-4 rounded-xl border border-slate-200 hover:border-emerald-300 transition bg-slate-50/50"
                >
                  <div className="flex justify-between items-start">
                    <div>
                      <h4 className="font-bold text-slate-900 text-sm">{member.full_name}</h4>
                      <div className="text-xs text-slate-500 flex items-center space-x-3 mt-1">
                        <span className="flex items-center space-x-1">
                          <Phone className="w-3 h-3 text-slate-400" />
                          <span>{member.phone}</span>
                        </span>
                        {member.emergency_contact_name && (
                          <span className="text-slate-400">
                            Emergency: {member.emergency_contact_name} ({member.emergency_contact_phone})
                          </span>
                        )}
                      </div>
                    </div>
                    <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-100 text-emerald-800 uppercase">
                      Active Member
                    </span>
                  </div>

                  {member.health_notes ? (
                    <div className="mt-3 p-2.5 rounded-lg bg-amber-50/80 border border-amber-200 flex items-start space-x-2 text-xs text-amber-900">
                      <AlertTriangle className="w-4 h-4 text-amber-600 flex-shrink-0 mt-0.5" />
                      <div>
                        <span className="font-bold">Health / Injury Note:</span> {member.health_notes}
                      </div>
                    </div>
                  ) : (
                    <div className="mt-2 text-[11px] text-slate-400 italic">
                      No medical precautions registered.
                    </div>
                  )}
                </div>
              ))
            )}
          </div>
        </div>

        {/* Right Col: Today's Personal Training Sessions */}
        <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="font-bold text-slate-900 text-sm flex items-center space-x-2">
              <Calendar className="w-4 h-4 text-indigo-600" />
              <span>Today's Sessions</span>
            </h3>
            <span className="text-xs bg-indigo-50 text-indigo-700 px-2 py-0.5 rounded font-semibold">
              Schedule
            </span>
          </div>

          <div className="space-y-3">
            {sessions.map((sess) => (
              <div
                key={sess.id}
                onClick={() => toggleSession(sess.id)}
                className={`p-3.5 rounded-xl border cursor-pointer transition ${
                  sess.completed
                    ? 'bg-slate-50 border-slate-200 opacity-60'
                    : 'bg-white border-slate-200 hover:border-emerald-400 shadow-xs'
                }`}
              >
                <div className="flex items-center justify-between text-xs mb-1">
                  <span className="font-bold text-emerald-700 flex items-center space-x-1">
                    <Clock className="w-3.5 h-3.5" />
                    <span>{sess.time}</span>
                  </span>
                  <span
                    className={`px-1.5 py-0.5 rounded text-[10px] font-bold uppercase ${
                      sess.completed
                        ? 'bg-emerald-100 text-emerald-800'
                        : 'bg-slate-100 text-slate-600'
                    }`}
                  >
                    {sess.completed ? 'Completed' : 'Upcoming'}
                  </span>
                </div>
                <div className="font-semibold text-slate-900 text-sm">{sess.memberName}</div>
                <div className="text-xs text-slate-500 mt-0.5">{sess.focus}</div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};
