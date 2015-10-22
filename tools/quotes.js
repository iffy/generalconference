angular.module('gc.quotes', [])

.value('DataUrl', '../data')

.factory('Server', function(DataUrl, $http, $q) {
  var Server = this;

  Server.conferences = [];
  Server.talks = {};

  Server._getConference = function(year, month) {
    var conf_dir = DataUrl + '/eng/' + year + '-' + month;
    $http.get(conf_dir + '/index.yml')
      .then(function(response) {
        var data = jsyaml.safeLoad(response.data);
        console.log('data', data);
        angular.forEach(data.items, function(item) {
          Server.talks[item.article_id] = item;
        });
        Server.conferences.push({
          month: month,
          year: year,
          talk_list: data.items
        });
        //console.log('Server.conferences', Server.conferences);
      })
  }

  Server.getTalkInfo = function(year, month, key) {
    var conf_dir = DataUrl + '/eng/' + year + '-' + month;
    var talk_dir = conf_dir + '/' + key;
    var text_d = $http.get(talk_dir + '/text.md')
      .then(function(response) {
        return response.data;
      })
    var meta_d = $http.get(talk_dir + '/metadata.yml')
      .then(function(response) {
        return jsyaml.safeLoad(response.data);
      }, function(error) {
        return null;
      })
    var time_d = $http.get(talk_dir + '/youtube_timing.yml')
      .then(function(response) {
        return jsyaml.safeLoad(response.data);
      }, function(error) {
        return null;
      })
    return $q.all([text_d, meta_d, time_d])
      .then(function(data) {
        return {
          text: data[0],
          metadata: data[1],
          timing: data[2],
        }
      })
  }

  Server._getConference(2015, 10);

  return Server;
})

.factory('splitByTiming', function() {
  return function(talk) {
    console.log('splitByTiming', talk);

    var timing_by_tcite = {};
    angular.forEach(talk.timing, function(time) {
      timing_by_tcite[time.tcite] = time;
    });

    // XXX DRY this off.
    // copyied from timingeditor.html
    var parsed = talk.text.split(/(\s+)/);
    var word_counts = {};
    var streams = [];
    var current_stream = [];
    streams.push({
      text: current_stream,
      start: '0',
      end: null
    });
    for (var i = 0; i < parsed.length; i++) {
      var word = parsed[i];
      if (/\s+/.test(word)) {
        // whitespace
        current_stream.push(word);
      } else {
        // text
        if (!word_counts[word]) {
          word_counts[word] = 0;
        }
        var tcite = '{' + word + '}' + word_counts[word];
        var timing = timing_by_tcite[tcite];
        if (timing) {
          // new keyframe
          current_stream = [];
          streams[streams.length-1].end = timing.seconds;
          streams.push({
            text: current_stream,
            start: timing.seconds,
            end: null,
          })
        }
        current_stream.push(word);
      }
    }
    angular.forEach(streams, function(stream) {
      stream.text = stream.text.join('');
    })
    return streams;
  }
})

.controller('QuotesCtrl', function($sce, Server, splitByTiming) {
  var ctrl = this;
  ctrl.quotes = [];
  ctrl.server = Server;

  ctrl.chooseTalk = function(talk) {
    Server.getTalkInfo(talk.year, talk.month, talk.key)
    .then(function(info) {
      console.log('info', info);
      if (info.timing) {
        info.streams = splitByTiming(info);
        ctrl.quotes.push(info);
      } else {
        // no timing info yet
      }
    })
  }

  ctrl.toggleStream = function(quote, stream) {
    console.log(quote);
    stream.used = !stream.used;
    quote.ranges = [];
    var last_start = null;
    var last_end = null;
    angular.forEach(quote.streams, function(s) {
      if (s.used) {
        console.log('used', s);
        if (last_end === s.start) {
          // continuation
          last_end = s.end;
        } else {
          // new range
          if (last_start !== null && last_end !== null) {
            quote.ranges.push([last_start, last_end]);
          }
          last_start = s.start;
          last_end = s.end;
        }
      }
    });
    quote.ranges.push([last_start, last_end]);
    angular.forEach(quote.ranges, function(range) {
      var start = range[0];
      var end = range[1];
      var embed = 'http://www.youtube.com/v/' + quote.metadata.youtube.id + '&start=' + Math.floor(start) + '&end=' + Math.ceil(end) + '&autoplay=1';
      embed = $sce.trustAs($sce.RESOURCE_URL, embed);
      range.push(embed);
    });
  }
  return ctrl;
});