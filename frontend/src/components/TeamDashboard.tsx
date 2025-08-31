/**
 * Team Productivity Dashboard Components
 * Comprehensive team analytics and insights
 */

import React, { useState, useEffect, useCallback } from 'react';

// Types and Interfaces
interface TeamMember {
    id: string;
    name: string;
    avatar: string;
    role: string;
    focusScore: number;
    productivityTrend: number;
    burnoutRisk: number;
    hoursWorked: number;
    tasksCompleted: number;
    collaborationScore: number;
    lastActive: string;
    peakHours: number[];
    status: 'active' | 'break' | 'offline';
}

interface TeamMetrics {
    avgFocusScore: number;
    focusScoreTrend: number;
    collaborationScore: number;
    collaborationTrend: number;
    avgBurnoutRisk: number;
    burnoutTrend: number;
    totalProductiveHours: number;
    teamProductivityScore: number;
    activeMembers: number;
    onBreakMembers: number;
}

interface AIInsight {
    id: string;
    type: 'recommendation' | 'alert' | 'achievement' | 'trend';
    title: string;
    description: string;
    priority: 'low' | 'medium' | 'high' | 'critical';
    actionItems: string[];
    confidence: number;
    timestamp: string;
    affectedMembers?: string[];
}

interface TimeRange {
    value: 'hour' | 'day' | 'week' | 'month';
    label: string;
}

interface TeamDashboard {
    teamId: string;
    teamName: string;
    members: TeamMember[];
    metrics: TeamMetrics;
    insights: AIInsight[];
    lastUpdated: string;
}

// Utility Components
const MetricCard: React.FC<{
    title: string;
    value: number | string;
    trend?: number;
    icon: React.ReactNode;
    alert?: boolean;
    unit?: string;
}> = ({ title, value, trend, icon, alert, unit }) => {
    const getTrendIcon = () => {
        if (trend === undefined) return null;
        if (trend > 0) return <span className="trend-up">↗️ +{Math.abs(trend).toFixed(1)}%</span>;
        if (trend < 0) return <span className="trend-down">↘️ -{Math.abs(trend).toFixed(1)}%</span>;
        return <span className="trend-neutral">→ 0%</span>;
    };

    return (
        <div className={`metric-card ${alert ? 'alert' : ''}`}>
            <div className="metric-header">
                <div className="metric-icon">{icon}</div>
                <h3 className="metric-title">{title}</h3>
            </div>
            <div className="metric-value">
                <span className="value">{value}{unit}</span>
                {getTrendIcon()}
            </div>
        </div>
    );
};

const InsightCard: React.FC<{ insight: AIInsight }> = ({ insight }) => {
    const getPriorityColor = (priority: string) => {
        switch (priority) {
            case 'critical': return '#e74c3c';
            case 'high': return '#e67e22';
            case 'medium': return '#f39c12';
            case 'low': return '#27ae60';
            default: return '#3498db';
        }
    };

    const getTypeIcon = (type: string) => {
        switch (type) {
            case 'recommendation': return '💡';
            case 'alert': return '⚠️';
            case 'achievement': return '🎉';
            case 'trend': return '📈';
            default: return 'ℹ️';
        }
    };

    return (
        <div className="insight-card" style={{ borderLeft: `4px solid ${getPriorityColor(insight.priority)}` }}>
            <div className="insight-header">
                <span className="insight-icon">{getTypeIcon(insight.type)}</span>
                <h4 className="insight-title">{insight.title}</h4>
                <span className="insight-confidence">Confidence: {Math.round(insight.confidence * 100)}%</span>
            </div>
            <p className="insight-description">{insight.description}</p>
            {insight.actionItems.length > 0 && (
                <div className="insight-actions">
                    <h5>Recommended Actions:</h5>
                    <ul>
                        {insight.actionItems.map((action, index) => (
                            <li key={index}>{action}</li>
                        ))}
                    </ul>
                </div>
            )}
            {insight.affectedMembers && insight.affectedMembers.length > 0 && (
                <div className="affected-members">
                    <span>Affects: {insight.affectedMembers.join(', ')}</span>
                </div>
            )}
        </div>
    );
};

const MemberCard: React.FC<{ member: TeamMember; onClick: (member: TeamMember) => void }> = ({ member, onClick }) => {
    const getStatusColor = (status: string) => {
        switch (status) {
            case 'active': return '#27ae60';
            case 'break': return '#f39c12';
            case 'offline': return '#95a5a6';
            default: return '#3498db';
        }
    };

    const getBurnoutRiskLevel = (risk: number) => {
        if (risk > 0.8) return 'Critical';
        if (risk > 0.6) return 'High';
        if (risk > 0.4) return 'Medium';
        return 'Low';
    };

    return (
        <div className="member-card" onClick={() => onClick(member)}>
            <div className="member-header">
                <div className="member-avatar">
                    <img src={member.avatar || '/default-avatar.png'} alt={member.name} />
                    <div 
                        className="status-indicator" 
                        style={{ backgroundColor: getStatusColor(member.status) }}
                    ></div>
                </div>
                <div className="member-info">
                    <h4 className="member-name">{member.name}</h4>
                    <p className="member-role">{member.role}</p>
                    <p className="member-last-active">Last active: {member.lastActive}</p>
                </div>
            </div>
            <div className="member-metrics">
                <div className="metric-row">
                    <span className="metric-label">Focus Score:</span>
                    <span className="metric-value">{(member.focusScore * 100).toFixed(0)}%</span>
                </div>
                <div className="metric-row">
                    <span className="metric-label">Tasks Completed:</span>
                    <span className="metric-value">{member.tasksCompleted}</span>
                </div>
                <div className="metric-row">
                    <span className="metric-label">Hours Worked:</span>
                    <span className="metric-value">{member.hoursWorked.toFixed(1)}h</span>
                </div>
                <div className="metric-row">
                    <span className="metric-label">Burnout Risk:</span>
                    <span className={`burnout-risk ${getBurnoutRiskLevel(member.burnoutRisk).toLowerCase()}`}>
                        {getBurnoutRiskLevel(member.burnoutRisk)}
                    </span>
                </div>
            </div>
        </div>
    );
};

const TimeRangeSelector: React.FC<{
    value: TimeRange['value'];
    onChange: (value: TimeRange['value']) => void;
}> = ({ value, onChange }) => {
    const timeRanges: TimeRange[] = [
        { value: 'hour', label: 'Last Hour' },
        { value: 'day', label: 'Today' },
        { value: 'week', label: 'This Week' },
        { value: 'month', label: 'This Month' }
    ];

    return (
        <div className="time-range-selector">
            {timeRanges.map((range) => (
                <button
                    key={range.value}
                    className={`time-range-button ${value === range.value ? 'active' : ''}`}
                    onClick={() => onChange(range.value)}
                >
                    {range.label}
                </button>
            ))}
        </div>
    );
};

// Main Dashboard Component
export const TeamProductivityDashboard: React.FC = () => {
    const [teamData, setTeamData] = useState<TeamDashboard | null>(null);
    const [timeRange, setTimeRange] = useState<TimeRange['value']>('week');
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [selectedMember, setSelectedMember] = useState<TeamMember | null>(null);
    const [autoRefresh, setAutoRefresh] = useState(true);

    // Mock API calls - replace with real API integration
    const fetchTeamData = useCallback(async (range: TimeRange['value']) => {
        setLoading(true);
        try {
            // Mock API delay
            await new Promise(resolve => setTimeout(resolve, 1000));
            
            // Generate mock data
            const mockData: TeamDashboard = {
                teamId: 'team_001',
                teamName: 'Product Development Team',
                members: generateMockMembers(),
                metrics: generateMockMetrics(),
                insights: generateMockInsights(),
                lastUpdated: new Date().toISOString()
            };
            
            setTeamData(mockData);
            setError(null);
        } catch (err) {
            setError('Failed to load team data');
            console.error('Error fetching team data:', err);
        } finally {
            setLoading(false);
        }
    }, []);

    // Generate mock team members
    const generateMockMembers = (): TeamMember[] => {
        const names = ['Alice Johnson', 'Bob Smith', 'Carol Davis', 'David Wilson', 'Eve Brown'];
        const roles = ['Frontend Developer', 'Backend Developer', 'Product Manager', 'Designer', 'QA Engineer'];
        
        return names.map((name, index) => ({
            id: `member_${index + 1}`,
            name,
            avatar: `/avatar${index + 1}.png`,
            role: roles[index],
            focusScore: 0.6 + Math.random() * 0.3,
            productivityTrend: (Math.random() - 0.5) * 20,
            burnoutRisk: Math.random() * 0.8,
            hoursWorked: 6 + Math.random() * 4,
            tasksCompleted: Math.floor(3 + Math.random() * 8),
            collaborationScore: 0.5 + Math.random() * 0.4,
            lastActive: new Date(Date.now() - Math.random() * 3600000).toLocaleTimeString(),
            peakHours: [9, 10, 14, 15],
            status: ['active', 'break', 'offline'][Math.floor(Math.random() * 3)] as any
        }));
    };

    // Generate mock team metrics
    const generateMockMetrics = (): TeamMetrics => ({
        avgFocusScore: 0.75,
        focusScoreTrend: 5.2,
        collaborationScore: 0.68,
        collaborationTrend: -2.1,
        avgBurnoutRisk: 0.35,
        burnoutTrend: 8.7,
        totalProductiveHours: 32.5,
        teamProductivityScore: 0.82,
        activeMembers: 4,
        onBreakMembers: 1
    });

    // Generate mock AI insights
    const generateMockInsights = (): AIInsight[] => [
        {
            id: 'insight_1',
            type: 'alert',
            title: 'Increased Burnout Risk Detected',
            description: 'Several team members are showing elevated stress indicators. Immediate action recommended.',
            priority: 'high',
            actionItems: [
                'Schedule team wellness check-in',
                'Implement mandatory break periods',
                'Review current workload distribution'
            ],
            confidence: 0.87,
            timestamp: new Date().toISOString(),
            affectedMembers: ['Alice Johnson', 'David Wilson']
        },
        {
            id: 'insight_2',
            type: 'recommendation',
            title: 'Optimize Meeting Schedule',
            description: 'Team productivity could improve by 15% with better meeting distribution.',
            priority: 'medium',
            actionItems: [
                'Move meetings away from peak focus hours (9-11 AM)',
                'Batch similar meetings together',
                'Implement no-meeting Fridays'
            ],
            confidence: 0.72,
            timestamp: new Date().toISOString()
        },
        {
            id: 'insight_3',
            type: 'achievement',
            title: 'Collaboration Score Improvement',
            description: 'Team collaboration has improved by 23% this week through better communication.',
            priority: 'low',
            actionItems: [
                'Continue current collaboration practices',
                'Document successful collaboration patterns',
                'Share best practices with other teams'
            ],
            confidence: 0.91,
            timestamp: new Date().toISOString()
        },
        {
            id: 'insight_4',
            type: 'trend',
            title: 'Focus Score Trending Upward',
            description: 'Team focus metrics show consistent improvement over the past two weeks.',
            priority: 'low',
            actionItems: [
                'Maintain current focus-enhancement strategies',
                'Analyze what factors contributed to improvement',
                'Set higher focus targets for next period'
            ],
            confidence: 0.65,
            timestamp: new Date().toISOString()
        }
    ];

    // Handle member selection
    const handleMemberClick = (member: TeamMember) => {
        setSelectedMember(member);
        // Could open detailed member view modal
        console.log('Selected member:', member);
    };

    // Auto-refresh functionality
    useEffect(() => {
        if (autoRefresh) {
            const interval = setInterval(() => {
                fetchTeamData(timeRange);
            }, 30000); // Refresh every 30 seconds

            return () => clearInterval(interval);
        }
    }, [autoRefresh, timeRange, fetchTeamData]);

    // Initial data load and time range changes
    useEffect(() => {
        fetchTeamData(timeRange);
    }, [timeRange, fetchTeamData]);

    if (loading && !teamData) {
        return (
            <div className="dashboard-loading">
                <div className="loading-spinner"></div>
                <p>Loading team productivity data...</p>
            </div>
        );
    }

    if (error) {
        return (
            <div className="dashboard-error">
                <h2>⚠️ Error Loading Dashboard</h2>
                <p>{error}</p>
                <button onClick={() => fetchTeamData(timeRange)}>Retry</button>
            </div>
        );
    }

    if (!teamData) {
        return (
            <div className="dashboard-empty">
                <h2>No team data available</h2>
                <p>Please check your team configuration and try again.</p>
            </div>
        );
    }

    return (
        <div className="team-dashboard">
            {/* Dashboard Header */}
            <div className="dashboard-header">
                <div className="header-main">
                    <h1>📊 {teamData.teamName} Productivity Hub</h1>
                    <p className="last-updated">
                        Last updated: {new Date(teamData.lastUpdated).toLocaleString()}
                    </p>
                </div>
                <div className="header-controls">
                    <TimeRangeSelector value={timeRange} onChange={setTimeRange} />
                    <div className="refresh-controls">
                        <label className="auto-refresh-toggle">
                            <input
                                type="checkbox"
                                checked={autoRefresh}
                                onChange={(e) => setAutoRefresh(e.target.checked)}
                            />
                            Auto-refresh
                        </label>
                        <button 
                            className="manual-refresh"
                            onClick={() => fetchTeamData(timeRange)}
                            disabled={loading}
                        >
                            🔄 Refresh
                        </button>
                    </div>
                </div>
            </div>

            {/* Key Metrics Grid */}
            <div className="metrics-grid">
                <MetricCard
                    title="Team Focus Score"
                    value={Math.round(teamData.metrics.avgFocusScore * 100)}
                    trend={teamData.metrics.focusScoreTrend}
                    icon={<span>🎯</span>}
                    unit="%"
                />
                <MetricCard
                    title="Collaboration Index"
                    value={Math.round(teamData.metrics.collaborationScore * 100)}
                    trend={teamData.metrics.collaborationTrend}
                    icon={<span>🤝</span>}
                    unit="%"
                />
                <MetricCard
                    title="Burnout Risk"
                    value={Math.round(teamData.metrics.avgBurnoutRisk * 100)}
                    trend={teamData.metrics.burnoutTrend}
                    icon={<span>⚡</span>}
                    alert={teamData.metrics.avgBurnoutRisk > 0.7}
                    unit="%"
                />
                <MetricCard
                    title="Productive Hours"
                    value={teamData.metrics.totalProductiveHours}
                    icon={<span>⏰</span>}
                    unit="h"
                />
                <MetricCard
                    title="Active Members"
                    value={`${teamData.metrics.activeMembers}/${teamData.members.length}`}
                    icon={<span>👥</span>}
                />
                <MetricCard
                    title="Team Productivity"
                    value={Math.round(teamData.metrics.teamProductivityScore * 100)}
                    icon={<span>📈</span>}
                    unit="%"
                />
            </div>

            {/* AI Insights Panel */}
            <div className="insights-panel">
                <h2>🤖 AI Team Insights</h2>
                <div className="insights-grid">
                    {teamData.insights.map(insight => (
                        <InsightCard key={insight.id} insight={insight} />
                    ))}
                </div>
            </div>

            {/* Team Members List */}
            <div className="members-section">
                <h2>👥 Team Members</h2>
                <div className="members-grid">
                    {teamData.members.map(member => (
                        <MemberCard 
                            key={member.id} 
                            member={member} 
                            onClick={handleMemberClick}
                        />
                    ))}
                </div>
            </div>

            {/* Quick Actions */}
            <div className="quick-actions">
                <h2>⚡ Quick Actions</h2>
                <div className="actions-grid">
                    <button className="action-button">
                        📋 Generate Team Report
                    </button>
                    <button className="action-button">
                        ⚠️ Send Wellness Check
                    </button>
                    <button className="action-button">
                        📅 Schedule Team Meeting
                    </button>
                    <button className="action-button">
                        🎯 Set Team Goals
                    </button>
                    <button className="action-button">
                        📊 Export Analytics
                    </button>
                    <button className="action-button">
                        🔔 Configure Alerts
                    </button>
                </div>
            </div>
        </div>
    );
};

// Supporting components for detailed views
export const MemberDetailModal: React.FC<{
    member: TeamMember | null;
    onClose: () => void;
}> = ({ member, onClose }) => {
    if (!member) return null;

    return (
        <div className="modal-overlay">
            <div className="member-detail-modal">
                <div className="modal-header">
                    <h2>{member.name} - Detailed View</h2>
                    <button className="close-button" onClick={onClose}>×</button>
                </div>
                <div className="modal-content">
                    {/* Detailed member analytics would go here */}
                    <p>Detailed analytics for {member.name}</p>
                    {/* Add charts, productivity timeline, etc. */}
                </div>
            </div>
        </div>
    );
};

export default TeamProductivityDashboard;