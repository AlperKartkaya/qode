import React, { useLayoutEffect } from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { Ionicons } from '@expo/vector-icons';

export default function SessionCard({ phoneNumber }) {
  // Generate mock correlation and flow IDs to match UX Flow
  const flowId = 'f_842a9d';
  const correlationId = 'c_0x4b7f';

  return (
    <View style={styles.card}>
      <View style={styles.cardHeader}>
        <Ionicons name="person" size={20} color="#4338CA" />
        <Text style={styles.cardTitle}>SESSION</Text>
      </View>
      
      <View style={styles.statusRow}>
        <View style={styles.badge}>
          <Ionicons name="checkmark-circle" size={14} color="#03543F" style={{marginRight: 4}} />
          <Text style={styles.badgeText}>Verified</Text>
        </View>
      </View>
      
      <View style={styles.divider} />
      
      <View style={styles.detailRow}>
        <Text style={styles.detailLabel}>Phone Number</Text>
        <Text style={styles.detailValue}>{phoneNumber}</Text>
      </View>
      <View style={styles.detailRow}>
        <Text style={styles.detailLabel}>Flow ID</Text>
        <Text style={styles.detailValue}>{flowId}</Text>
      </View>
      <View style={styles.detailRow}>
        <Text style={styles.detailLabel}>Correlation ID</Text>
        <Text style={styles.detailValue}>{correlationId}</Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  card: { backgroundColor: '#FFFFFF', padding: 20, borderRadius: 12, marginBottom: 16, shadowColor: '#000', shadowOffset: { width: 0, height: 1 }, shadowOpacity: 0.1, shadowRadius: 4, elevation: 2 },
  cardHeader: { flexDirection: 'row', alignItems: 'center', marginBottom: 16 },
  cardTitle: { fontSize: 13, fontWeight: '700', color: '#6B7280', marginLeft: 8, letterSpacing: 1 },
  statusRow: { flexDirection: 'row', marginBottom: 16 },
  badge: { flexDirection: 'row', alignItems: 'center', backgroundColor: '#DEF7EC', paddingHorizontal: 12, paddingVertical: 6, borderRadius: 20 },
  badgeText: { fontSize: 13, fontWeight: '700', color: '#03543F' },
  divider: { height: 1, backgroundColor: '#F3F4F6', marginBottom: 12 },
  detailRow: { flexDirection: 'row', justifyContent: 'space-between', paddingVertical: 6 },
  detailLabel: { color: '#6B7280', fontSize: 14, fontWeight: '500' },
  detailValue: { color: '#111827', fontSize: 14, fontWeight: '600', fontFamily: 'Courier' },
});
